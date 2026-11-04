#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FT2232H MPSSE 在线硬件诊断与 JTAG 信号质量（误码率）测试工具
直接调用 Vivado 自带的 FTD2XX.dll，无需安装任何第三方 Python 库。
包含三项核心测试：
  1. EEPROM User Area 签名校验
  2. ADBUS GPIO 逐位驱动与回读诊断（定位短路、虚焊、缓冲器方向错误）
  3. JTAG 扫描链 IDCODE 识别与 1MHz ~ 30MHz 全速率回环压力测试（BER 误码率与环路延迟评估）
"""

import ctypes
import struct
import time

FTD2XX_DLL_PATH = r"D:\AMDDesignTools\2025.2\Vivado\lib\win64.o\FTD2XX.dll"


class FT2232HMpsseTester:
    def __init__(self, dll_path=FTD2XX_DLL_PATH, dev_index=0):
        self.dll = ctypes.WinDLL(dll_path)
        self.handle = ctypes.c_void_p()
        self.dev_index = dev_index

    def open_and_init_mpsse(self):
        status = self.dll.FT_Open(self.dev_index, ctypes.byref(self.handle))
        if status != 0:
            raise RuntimeError(f"FT_Open({self.dev_index}) 失败，状态码={status}（请先关闭 Vivado hw_server 释放端口）")

        self.dll.FT_ResetDevice(self.handle)
        self.dll.FT_SetUSBParameters(self.handle, 65536, 65535)
        self.dll.FT_SetChars(self.handle, 0, 0, 0, 0)
        self.dll.FT_SetTimeouts(self.handle, 1000, 1000)
        self.dll.FT_SetLatencyTimer(self.handle, 2)

        # 先复位 BitMode (0x00)，再进入 MPSSE 模式 (0x02)
        self.dll.FT_SetBitMode(self.handle, 0x00, 0x00)
        time.sleep(0.02)
        self.dll.FT_SetBitMode(self.handle, 0x00, 0x02)
        time.sleep(0.02)
        self.dll.FT_Purge(self.handle, 3)

    def close(self):
        if self.handle.value:
            # 恢复安全闲置态：TMS=1, JTAG_OE=1(关闭缓冲器输出)
            self.write(b"\x80\xe8\xeb\x87")
            self.dll.FT_Close(self.handle)
            self.handle = ctypes.c_void_p()

    def write(self, data: bytes):
        buf = (ctypes.c_ubyte * len(data))(*data)
        written = ctypes.c_uint32()
        st = self.dll.FT_Write(self.handle, buf, len(data), ctypes.byref(written))
        if st != 0 or written.value != len(data):
            raise RuntimeError(f"FT_Write 失败: status={st}, written={written.value}/{len(data)}")

    def read(self, nbytes: int) -> bytes:
        buf = (ctypes.c_ubyte * nbytes)()
        read_cnt = ctypes.c_uint32()
        st = self.dll.FT_Read(self.handle, buf, nbytes, ctypes.byref(read_cnt))
        if st != 0:
            raise RuntimeError(f"FT_Read 失败: status={st}")
        return bytes(buf[: read_cnt.value])

    def check_eeprom_signature(self):
        print("=" * 72)
        print("[步骤 1] 检查 EEPROM User Area (Xilinx JTAG 固件签名)")
        print("=" * 72)
        ua_size = ctypes.c_uint32()
        self.dll.FT_EE_UASize(self.handle, ctypes.byref(ua_size))
        ua_buf = (ctypes.c_ubyte * 64)()
        ua_read = ctypes.c_uint32()
        self.dll.FT_EE_UARead(self.handle, ua_buf, 64, ctypes.byref(ua_read))
        raw = bytes(ua_buf[:32])
        fwid = struct.unpack_from("<I", raw, 0)[0]
        strings = raw[4:].split(b"\x00")
        vendor = strings[0].decode("utf-8", errors="ignore") if len(strings) > 0 else ""
        board = strings[1].decode("utf-8", errors="ignore") if len(strings) > 1 else ""
        print(f"  User Area 容量 : {ua_size.value} Bytes")
        print(f"  Firmware ID    : 0x{fwid:08x} ({'正常: FT2232H' if fwid == 0x584A0003 else '异常!'})")
        print(f"  Vendor / Board : '{vendor}' / '{board}'")

    def diagnose_adbus_pins(self):
        print("\n" + "=" * 72)
        print("[步骤 2] MPSSE ADBUS0~7 逐位驱动与物理引脚电平回读诊断")
        print("=" * 72)
        # 方向掩码 0xEB = 1110_1011b:
        #   Bit 0 (ADBUS0 FT_TCK)  = 1 (输出)
        #   Bit 1 (ADBUS1 FT_TDI)  = 1 (输出)
        #   Bit 2 (ADBUS2 FT_TDO)  = 0 (输入)
        #   Bit 3 (ADBUS3 FT_TMS)  = 1 (输出)
        #   Bit 4 (ADBUS4 FPGA_ON) = 0 (输入，读取目标板 VREF 比较器 U5 输出)
        #   Bit 5 (ADBUS5 JTAG_OE) = 1 (输出，低电平有效使能 U4)
        #   Bit 6,7 (ADBUS6,7)     = 1 (输出，保持高电平)
        test_vectors = [
            (0xE0, "OE_N=1(关断U4), TCK=0, TDI=0, TMS=0 -> 检查 U1 本身引脚是否对电源/地短路"),
            (0xC0, "OE_N=0(使能U4), TCK=0, TDI=0, TMS=0 -> 检查全零驱动"),
            (0xC1, "OE_N=0(使能U4), TCK=1, TDI=0, TMS=0 -> 单独翻转 FT_TCK (Bit 0)"),
            (0xC2, "OE_N=0(使能U4), TCK=0, TDI=1, TMS=0 -> 单独翻转 FT_TDI (Bit 1)"),
            (0xC8, "OE_N=0(使能U4), TCK=0, TDI=0, TMS=1 -> 单独翻转 FT_TMS (Bit 3)"),
            (0xCB, "OE_N=0(使能U4), TCK=1, TDI=1, TMS=1 -> 全高驱动"),
        ]

        output_mask = 0xEB  # 仅比较输出引脚 Bit 0,1,3,5,6,7
        all_passed = True
        for val, desc in test_vectors:
            # 0x80: 设置 ADBUS 值与方向; 0x81: 回读 ADBUS 真实引脚电压; 0x87: 立即刷新发送
            self.write(bytes([0x80, val, output_mask, 0x81, 0x87]))
            read_val = self.read(1)[0]
            mismatch = (val ^ read_val) & output_mask
            status_str = "PASS" if mismatch == 0 else f"FAIL (异常位掩码=0x{mismatch:02x})"
            if mismatch != 0:
                all_passed = False
            print(f"  写 0x{val:02x} ({val:08b}) -> 读 0x{read_val:02x} ({read_val:08b}) [{status_str}]")
            print(f"     说明: {desc}")

        fpga_on = (read_val >> 4) & 1
        print(f"\n  -> 目标板供电检测 ADBUS4 (FPGA_ON): {fpga_on} ({'已检测到目标板 3.3V' if fpga_on else '未检测到目标板供电!'})")
        print(f"  -> 引脚逐位诊断总结: {'全部通过 (无短路/死锁)' if all_passed else '存在硬件短路或冲突!'}")
        return all_passed

    def set_jtag_frequency(self, freq_hz: int):
        # FT2232H 关闭 5 分频 (0x8A) 时基准时钟为 30MHz: TCK = 30MHz / (1 + divisor)
        divisor = max(0, int(round(30_000_000 / freq_hz)) - 1)
        actual_freq = 30_000_000 / (1 + divisor)
        div_low = divisor & 0xFF
        div_high = (divisor >> 8) & 0xFF
        # 0x8A: 关闭5分频; 0x85: 关闭自适应时钟; 0x86: 设置分频系数; 0x80 0xC8 0xEB: 使能 JTAG_OE=0
        self.write(bytes([0x8A, 0x85, 0x86, div_low, div_high, 0x80, 0xC8, 0xEB, 0x87]))
        return actual_freq

    def scan_idcodes_and_ber_test(self, freq_hz: int, neg_edge_sample: bool = False, iterations: int = 200):
        actual_freq = self.set_jtag_frequency(freq_hz)
        # 0x39: 负沿发 TDI, 正沿采 TDO (标准模式，适用于环路延迟 < T_half 的速率，即 <=15MHz)
        # 0x3D: 负沿发 TDI, 负沿采 TDO (高速补偿模式，允许整周期 33.3ns 环路延迟，适用于 30MHz)
        shift_opcode = 0x3D if neg_edge_sample else 0x39
        pattern = b"\xA5\x5A\xF0\x0F\x12\x34\x56\x78\x9A\xBC\xDE\xF0\x55\xAA\x33\xCC"
        expected_tail = pattern[:8]

        error_bits = 0
        total_bits = iterations * 64
        idcodes = None

        for _ in range(iterations):
            cmd = bytes([0x4B, 0x05, 0x1F, 0x4B, 0x02, 0x01, shift_opcode, 0x0F, 0x00]) + pattern + b"\x87"
            self.write(cmd)
            rx = self.read(16)
            if idcodes is None:
                id0, id1 = struct.unpack_from("<II", rx, 0)
                idcodes = (id0, id1)
            rx_tail = rx[8:16]
            if rx_tail != expected_tail:
                for b1, b2 in zip(rx_tail, expected_tail):
                    error_bits += bin(b1 ^ b2).count("1")

        return actual_freq, idcodes, error_bits, total_bits


if __name__ == "__main__":
    tester = FT2232HMpsseTester()
    try:
        tester.open_and_init_mpsse()
        tester.check_eeprom_signature()
        tester.diagnose_adbus_pins()

        print("\n" + "=" * 72)
        print("[步骤 3] JTAG 链 IDCODE 识别与 1MHz ~ 30MHz 全速率误码率 (BER) 测试")
        print("=" * 72)
        test_configs = [
            (1_000_000, False, "标准正沿采样 (0x39)"),
            (5_000_000, False, "标准正沿采样 (0x39)"),
            (10_000_000, False, "标准正沿采样 (0x39)"),
            (15_000_000, False, "标准正沿采样 (0x39)"),
            (30_000_000, False, "正沿采样 (0x39, 半周期16.7ns < 环路延迟~17.5ns)"),
            (30_000_000, True, "负沿采样 (0x3D, 整周期33.3ns > 环路延迟~17.5ns)"),
        ]
        for f, neg_edge, mode_desc in test_configs:
            actual_f, ids, err, tot = tester.scan_idcodes_and_ber_test(f, neg_edge_sample=neg_edge, iterations=500)
            ber = err / tot
            print(
                f"  TCK = {actual_f/1e6:5.1f} MHz [{mode_desc}]\n"
                f"     -> IDCODE = [0x{ids[0]:08x}, 0x{ids[1]:08x}] | 误码 = {err}/{tot} bits (BER = {ber:.2e})"
            )
    finally:
        tester.close()
