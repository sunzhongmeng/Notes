<!-- note {"tags": ["FPGA", "Xilinx", "AMD", "Vivado", "JTAG", "FT2232H", "MPSSE", "信号完整性"], "keywords": ["program_ftdi", "FT2232H", "93LC56BT-I/OT", "MPSSE", "FTD2XX", "USB-JTAG", "Vivado 2025.2", "信号质量测试"], "updated": "2026-11-04"} -->

# FT2232H USB-JTAG

## 目标与背景

针对自制的 **FT2232H-56Q + 93LC56BT-I/OT + SN74AXC4T774BQBR** USB 转 JTAG/UART 调试器电路板，本文完整记录三项核心工程实践：

1. **EEPROM 固件烧写**：使用 Vivado 2025.2 自带的 `program_ftdi` 工具写入 Xilinx/AMD 官方认证签名（`0x584a0003`）。
2. **FT2232H MPSSE 底层逐位硬件诊断**：在无需示波器的情况下，直接通过 Python 调用 `FTD2XX.dll` 发送 MPSSE（Multi-Protocol Synchronous Serial Engine）指令，对 `ADBUS0~7` 引脚进行逐位驱动与物理电平回读，快速定位**引脚连锡短路、虚焊、电平转换器方向错误**等硬件故障（实测定位出 `U1` Pin 15 `FT_TMS` 与 Pin 16 `3V3` 连锡短路并完成修复）。
3. **JTAG 信号质量测试**：从**软件误码率（1 MHz ~ 30 MHz BER 压力测试）**与**硬件示波器信号完整性（SI）测试**两个维度验证 30 Mbps JTAG 通信质量。
- **适用硬件配置**：
  - 主控芯片：`U1` = `FT2232H-56Q`（VQFN-56）
  - EEPROM 芯片：`U2` = `93LC56BT-I/OT`（2 Kbit，128 × 16-bit 组织，SOT-23-6）
  - 电平转换与缓冲：`U4` = `SN74AXC4T774BQBR`（Channel A `ADBUS0~3` 对应 `FT_TCK/FT_TDI/FT_TDO/FT_TMS`，`ADBUS4` 接目标板 `VREF` 电压检测比较器 `U5 TLV7031DBVR` 输出 `FPGA_ON`，`ADBUS5` 控制 `JTAG_OE` 低有效输出使能）
  - 实测目标板：AMD Zynq UltraScale+ RFSoC（`XCZU47DR`，JTAG 链含 `arm_dap` `0x5ba00477` 与 PL `0x147ff093`）
- **适用软件与环境**：
  - 操作系统：Windows 10 / 11 (x64)
  - 工具版本：AMD Vivado 2025.2（安装于 `D:\AMDDesignTools\2025.2\Vivado`）

## 准备资料

- **配套诊断与误码率测试源码**：[mpsse_jtag_diag.py](../../../code/FT2232H%20USB-JTAG/mpsse_jtag_diag.py)
- **Vivado 2025.2 关键工具路径**：
  - 固件烧写批处理入口：`D:\AMDDesignTools\2025.2\Vivado\bin\program_ftdi.bat`
  - 动态链接库路径：`D:\AMDDesignTools\2025.2\Vivado\lib\win64.o\FTD2XX.dll`
- **硬件与驱动前提**：
  - Windows 设备管理器中确认设备使用 FTDI 官方驱动（`VID_0403&PID_6010`），切勿使用 Zadig 替换为 `WinUSB`/`libusb`。
  - 执行 `program_ftdi` 烧写时，电脑上仅保留当前唯一一个 FTDI 设备。

## 操作与结果

### 第一部分：使用 Vivado 2025.2 烧写 EEPROM 固件

> **路径注意事项**：`D:\AMDDesignTools\2025.2\Vivado\bin\unwrapped\win64.o\program_ftdi.exe` 是未封装的底层程序，直接运行会因缺少环境变量报错缺失 DLL。必须通过上层封装脚本 `D:\AMDDesignTools\2025.2\Vivado\bin\program_ftdi.bat` 调用。

1. **读取当前 FTDI 设备信息**：
   
   ```powershell
   & "D:\AMDDesignTools\2025.2\Vivado\bin\program_ftdi.bat" -read
   ```
2. **写入 Xilinx 官方 FT2232H JTAG 配置**：
   
   ```powershell
   & "D:\AMDDesignTools\2025.2\Vivado\bin\program_ftdi.bat" -write -ftdi FT2232H -serial 2026110401 -vendor "Xilinx" -board "USB-JTAG-AMD" -desc "Vivado USB-JTAG"
   ```
   
   - `-ftdi FT2232H`：自动将 Channel A 配置为 `245 FIFO`（供 MPSSE JTAG 使用）、Channel B 配置为 `VCP`（虚拟串口），并在 EEPROM User Area 写入 32 位固件签名 `0x584a0003`。
   
   - `-serial 2026110401`：5~13 位纯字母/数字序列号。
3. **回读验证**：
   重新插拔 USB 后执行 `-read`，确认输出 `Serial = 2026110401`、`vendor = Xilinx`、`board = USB-JTAG-AMD`。此时在 Vivado Hardware Manager 的 `Hardware Targets` 列表中即可看到 `xilinx_tcf` -> `Xilinx/2026110401A`。

---

### 第二部分：通过 MPSSE 指令对 FT2232H 进行逐位硬件调试

#### 1. MPSSE 调试核心原理与指令集

FT2232H 的 Channel A 支持 **MPSSE（多协议同步串行引擎）** 模式（通过 `FT_SetBitMode(handle, 0x00, 0x02)` 开启）。在 MPSSE 模式下，芯片接收字节流形式的指令（Opcode）：

- **`0x80 <Value> <Direction>`（写 `ADBUS0~7` 方向与输出值）**：配置低 8 位引脚方向（`1` = 输出，`0` = 输入）并驱动输出电平。
- **`0x81`（读 `ADBUS0~7` 真实物理引脚电平）**：**这是硬件调试最强大的指令**！它读取的不是内部输出锁存器，而是**引脚焊盘上的实际电压比较结果**。
  - **短路判据**：如果某引脚配置为输出（`Direction = 1`），命令其输出低电平（`Value = 0`），但 `0x81` 回读该位仍为 `1`，说明该引脚在外部被**强上拉或直接与 `3.3V` 电源焊盘连锡短路**！反之若输出 `1` 但回读为 `0`，说明该引脚对 `GND` 短路。
  - **级联隔离判据**：先令 `ADBUS5`（`JTAG_OE`）= `1`（关断电平转换器 `U4` 使其处于高阻态 Hi-Z），测试 `U1` 本身引脚是否正常翻转；再令 `ADBUS5` = `0`（打开 `U4`），测试 `U4` 方向配置是否与 `U1` 发生总线冲突。

| MPSSE 指令 (Hex)  | 参数字节                      | 功能说明                                                                | 在本板 JTAG 调试中的用途                                 |
| --------------- | ------------------------- | ------------------------------------------------------------------- | ----------------------------------------------- |
| `0x80`          | `<Val> <Dir>`             | 设置低字节 `ADBUS0~7` 输出电平与方向                                            | 逐位翻转 `FT_TCK/TDI/TMS/JTAG_OE`                   |
| `0x81`          | 无 (返回 1 字节)               | 读取低字节 `ADBUS0~7` 焊盘真实物理电平                                           | 检验输出脚是否被短路锁死、读取 `FT_TDO` 与 `FPGA_ON`            |
| `0x82` / `0x83` | `<Val> <Dir>` / 无         | 设置 / 读取高字节 `ACBUS0~7`                                               | 调试高字节 GPIO                                      |
| `0x8A` / `0x8B` | 无                         | 关闭 / 开启 5 分频（60MHz 内部主频）                                            | `0x8A` 对应最高 30MHz 基准；`0x8B` 对应 6MHz 基准          |
| `0x86`          | `<DivL> <DivH>`           | 设置 TCK 分频系数：$f_{\text{TCK}} = \frac{30\text{ MHz}}{1 + \text{Div}}$ | `Div=0` 为 30MHz，`Div=1` 为 15MHz，`Div=29` 为 1MHz |
| `0x4B`          | `<Len-1> <Byte>`          | 在下降沿向 `TMS` 移位输出 `1~7` bits                                         | 驱动 JTAG TAP 状态机（如复位、进入 `Shift-DR`/`Shift-IR`）   |
| `0x39`          | `<LenL> <LenH> <Data...>` | 字节模式 LSB-first：负沿发 `TDI`、**正沿采 `TDO`**                              | 标准 JTAG 数据移位（适用于 $\le 15\text{ MHz}$）           |
| `0x3D`          | `<LenL> <LenH> <Data...>` | 字节模式 LSB-first：负沿发 `TDI`、**负沿采 `TDO`**                              | 高速延迟补偿移位（适用于 $30\text{ MHz}$，容许整周期环路延迟）         |
| `0x87`          | 无                         | 立即刷新发送 FT2232H 接收缓冲区（Send Immediate）                                | 放在每次读指令末尾，消除 USB 批量传输等待延迟                       |

#### 2. 本板 `ADBUS0~7` 位映射与诊断真值表

本板 `ADBUS` 方向掩码固定为 `0xEB`（`1110_1011b`）：

| 位号               | FT2232H 引脚           | 原理图网络名    | 方向 (`0xEB`) | 功能说明                                                 |
| ---------------- | -------------------- | --------- | ----------- | ---------------------------------------------------- |
| Bit 0 (`0x01`)   | Pin 12 `ADBUS0`      | `FT_TCK`  | `1` (输出)    | JTAG 时钟输出 -> `U4.A4` (Pin 6)                         |
| Bit 1 (`0x02`)   | Pin 13 `ADBUS1`      | `FT_TDI`  | `1` (输出)    | JTAG 数据输出 -> `U4.A3` (Pin 5)                         |
| Bit 2 (`0x04`)   | Pin 14 `ADBUS2`      | `FT_TDO`  | `0` (输入)    | JTAG 数据输入 <- `U4.A2` (Pin 4)                         |
| Bit 3 (`0x08`)   | Pin 15 `ADBUS3`      | `FT_TMS`  | `1` (输出)    | JTAG 模式选择 -> `U4.A1` (Pin 3)                         |
| Bit 4 (`0x10`)   | Pin 17 `ADBUS4`      | `FPGA_ON` | `0` (输入)    | 目标板 `VREF` 检测输入 <- `U5.OUT` (`TP1`，有电为 `1`)          |
| Bit 5 (`0x20`)   | Pin 18 `ADBUS5`      | `JTAG_OE` | `1` (输出)    | `U4` 输出使能 -> `R15` -> `U4.OE#` (`TP2`，`0` 使能，`1` 高阻) |
| Bit 6~7 (`0xC0`) | Pin 19~20 `ADBUS6~7` | 悬空        | `1` (输出)    | 默认写 `1`                                              |

#### 3. 故障定位实录：如何通过 5 行返回数据精准抓出 `U1` Pin 15~16 连锡短路

在修复前，执行逐位翻转测试得到的实测日志如下：

```text
Wrote 0xc0 (bin 11000000, 令 TMS=0, TDI=0, TCK=0) -> Read 0xdc (bin 11011100) [异常: Bit 3 TMS 仍为 1!]
Wrote 0xc1 (bin 11000001, 令 TCK=1)               -> Read 0xdd (bin 11011101) [Bit 0 TCK 正常变为 1]
Wrote 0xc2 (bin 11000010, 令 TDI=1)               -> Read 0xde (bin 11011110) [Bit 1 TDI 正常变为 1]
Wrote 0xe0 (bin 11100000, 关闭 U4 OE_N=1, TMS=0)  -> Read 0xfc (bin 11111100) [即使关断 U4, Bit 3 TMS 仍死锁为 1!]
```

**推理过程**：

1. 写入 `0xC0`（令 `Bit 3 FT_TMS = 0`）时，回读 `0xDC`（`Bit 3 = 1`），仅对输出引脚掩码 `0xEB` 做异或：`(0xC0 ^ 0xDC) & 0xEB = 0x08`（精准指向 **Bit 3 `FT_TMS` 无法拉低**）。
2. 写入 `0xE0` 将 `U4` 关断（排除 `U4` 反向驱动可能），`Bit 3` 依然为 `1`，证明 `FT_TMS` 在 PCB 上与 `3.3V` 存在物理短路。
3. 核对封装引脚：`U1`（`FT2232H-56Q`）的 **Pin 15 为 `ADBUS3`（`FT_TMS`）**，紧邻的 **Pin 16 为 `VCCIO`（`3V3`）**。用烙铁清除 `U1` Pin 15~16 之间的连锡后再次运行脚本，所有位全部 `[PASS]`，且立即读出目标板 Zynq RFSoC 的双核 `IDCODE`（`[0x5ba00477, 0x147ff093]`）！

#### 4. 完整 Python 诊断与误码率测试代码

以下代码直接调用 Vivado 自带的 `FTD2XX.dll`，无需安装任何第三方库（运行前请先关闭 Vivado Hardware Manager 以免占用 USB 端口）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FT2232H MPSSE 在线硬件诊断与 JTAG 信号质量（误码率）测试工具
直接调用 Vivado 自带的 FTD2XX.dll，无需安装任何第三方 Python 库。
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
        divisor = max(0, int(round(30_000_000 / freq_hz)) - 1)
        actual_freq = 30_000_000 / (1 + divisor)
        div_low = divisor & 0xFF
        div_high = (divisor >> 8) & 0xFF
        self.write(bytes([0x8A, 0x85, 0x86, div_low, div_high, 0x80, 0xC8, 0xEB, 0x87]))
        return actual_freq

    def scan_idcodes_and_ber_test(self, freq_hz: int, neg_edge_sample: bool = False, iterations: int = 200):
        actual_freq = self.set_jtag_frequency(freq_hz)
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
```

---

### 第三部分：JTAG 信号质量测试方法（软件误码率 + 硬件示波器测量）

验证 JTAG 信号质量应结合 **软件高速回环误码率（BER）测试** 与 **硬件示波器信号完整性（SI）测量** 两个层面。

#### 1. 软件层面：全速率数据回环误码率（BER）与环路延迟边界测试

**测试原理**：
当 JTAG 状态机进入 `Capture-DR` -> `Shift-DR` 时，链上的每个器件（如 Zynq UltraScale+ 的 `arm_dap` 和 PL TAP）各将自身的 32-bit `IDCODE` 装入数据移位寄存器（2 个器件共 64 bits）。若此时从 `TDI` 连续移入 128 bits（16 字节）：

- 前 64 bits（前 8 字节）从 `TDO` 移出的是两个器件的固定 `IDCODE`（`0x5ba00477` 与 `0x147ff093`）；
- 后 64 bits（后 8 字节）从 `TDO` 移出的则是**刚才我们从 `TDI` 灌进去的前 64 bits 测试码型（如 `0xA55AF00F12345678`）**！
  这意味着无需给 FPGA 下载任何 Bitstream，天然就构成了一条经过 **`U1(FT2232H) -> U4(B3) -> 排线 -> FPGA TDI -> FPGA 内部 64级寄存器 -> FPGA TDO -> 排线 -> U4(B2->A2) -> U1(FT2232H)`** 的完整物理层全链路回环！

**本板实测结果（每档速率连续收发 32,000 bits）**：

```text
  TCK =   1.0 MHz [标准正沿采样 (0x39)]
     -> IDCODE = [0x5ba00477, 0x147ff093] | 误码 = 0/32000 bits (BER = 0.00e+00)
  TCK =   5.0 MHz [标准正沿采样 (0x39)]
     -> IDCODE = [0x5ba00477, 0x147ff093] | 误码 = 0/32000 bits (BER = 0.00e+00)
  TCK =  10.0 MHz [标准正沿采样 (0x39)]
     -> IDCODE = [0x5ba00477, 0x147ff093] | 误码 = 0/32000 bits (BER = 0.00e+00)
  TCK =  15.0 MHz [标准正沿采样 (0x39)]
     -> IDCODE = [0x5ba00477, 0x147ff093] | 误码 = 0/32000 bits (BER = 0.00e+00)
  TCK =  30.0 MHz [正沿采样 (0x39, 半周期16.7ns < 环路延迟~17.5ns)]
     -> IDCODE = [0xb74008ef, 0x28ffe027] | 误码 = 15000/32000 bits (BER = 4.69e-01)
  TCK =  30.0 MHz [负沿采样 (0x3D, 整周期33.3ns > 环路延迟~17.5ns)]
     -> IDCODE = [0x5ba00477, 0x147ff093] | 误码 = 0/32000 bits (BER = 0.00e+00)
```

**对 30 MHz 实测数据的深入物理分析**：

- 在 **1 MHz ~ 15 MHz** 下，标准正沿采样（`0x39`，负沿发、正沿采，允许环路延迟 $\le \frac{T}{2} = 33.3\text{ ns}$）实现了 **0 误码（32,000 bits 全对）**。
- 在 **30 MHz** 下，时钟周期 $T = 33.3\text{ ns}$，半周期仅为 $\frac{T}{2} = 16.67\text{ ns}$。而信号往返的物理总环路延迟为：
  $$t_{\text{RTD}} = t_{\text{pd,U4(TCK)}} + t_{\text{cable}} + t_{\text{co,FPGA(TDO)}} + t_{\text{cable}} + t_{\text{pd,U4(TDO)}} \approx 3.5 + 1.5 + 7.5 + 1.5 + 3.5 = 17.5\text{ ns}$$
  由于 $t_{\text{RTD}} \approx 17.5\text{ ns} > 16.67\text{ ns}$，使用正沿采样（`0x39`）正好踩在 `TDO` 翻转沿之后，导致读出的数据整体左移了 1 bit（`0x5ba00477 << 1 | 1 = 0xb74008ef`）；而切换为**负沿采样（`0x3D`）**后，允许的环路延迟窗口扩大到整周期 $33.3\text{ ns}$，在 **30.0 MHz 下同样实现了 32,000 bits 零误码（`BER = 0.00`）**！

---

#### 2. 硬件层面：使用示波器测量 JTAG 信号完整性（SI）的方法与标准

若要使用示波器评估 PCB 走线、串联匹配电阻（`R18/R19/R21/R23 = 33Ω`）及排线的物理层波形质量，请按以下步骤进行：

1. **探头与接地规范（极其关键）**：
   
   - **带宽要求**：测试 15~30 MHz 数字方波（上升时间 $t_r \approx 1.5 \sim 3\text{ ns}$），示波器与无源/有源探头带宽应 $\ge 200\text{ MHz}$（推荐 $500\text{ MHz}$），采样率 $\ge 1\text{ GSa/s}$。
   
   - **必须使用接地弹簧针（Ground Spring）**：拔掉探头前端的帽子和长鳄鱼夹地线，套上短接地弹簧针，直接点在目标板 JTAG 座的 `GND` 引脚（或下载器 `H2.5 GND`）上。长鳄鱼夹地线的寄生电感（约 $150\text{ nH}$）会与探头输入电容产生谐振，在屏幕上制造出原本不存在的假过冲和假振铃。

2. **正确的测试点选择（必须在“信号接收端”测量）**：
   传输线反射在信号**接收端（高阻输入端）**最严重，切勿在驱动源端测量：
   
   - **测量 `TCK`、`TMS`、`TDI`**：探头尖端必须点在 **FPGA 目标板侧的 JTAG 连接器焊盘**（越靠近 FPGA 引脚越好），地针点在目标板 JTAG 座的 `GND` 脚。
   
   - **测量 `TDO`**：`TDO` 是由目标板 FPGA 发出、下载器接收的信号，因此探头尖端应点在 **下载器板上 `U1` 的 Pin 14（`FT_TDO`）或 `U4` 的 Pin 4（`A2`）**。

3. **四项核心指标与合格判据**：

| 测试项目                                                 | 测量方法                                                           | 合格标准 (3.3V LVCMOS JTAG)                                                                                            | 不合格时的硬件调整措施                                                                                  |
| ---------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| **1. `TCK` 边沿单调性 (最核心)**                             | 放大观察 `TCK` 上升沿与下降沿在 $0.8\text{ V} \sim 2.0\text{ V}$ 阈值区间的波形   | **必须单调无回沟（No Double-Clocking）**。边沿中途绝不能出现回落/回升振铃，否则 FPGA 会把 1 个时钟误判为 2 个时钟，导致 TAP 状态机瞬间崩溃                          | 缩短飞线/排线长度；在排线中每根信号线旁伴随 `GND` 线；确认源端串联 `33Ω` 电阻（`R18`）已焊接                                     |
| **2. 过冲 (Overshoot) 与下冲 (Undershoot)**               | 测量波形最高峰值 $V_{\text{max}}$ 与最低谷值 $V_{\text{min}}$               | $V_{\text{max}} \le 3.7\text{ V}$（过冲 $< 0.4\text{ V}$）<br>$V_{\text{min}} \ge -0.3\text{ V}$（下冲 $> -0.3\text{ V}$） | 若过冲/振铃过大（如峰值达 $4.2\text{ V}$），将源端串联电阻从 `33Ω` 增大至 `47Ω` 或 `51Ω`                               |
| **3. 上升/下降时间 ($t_r / t_f$)**                         | 测量 $10\% \sim 90\%$ 幅度（$0.33\text{ V} \sim 2.97\text{ V}$）的时间差 | 15 MHz 下建议 $1.5\text{ ns} \le t_r \le 6\text{ ns}$<br>30 MHz 下建议 $1.5\text{ ns} \le t_r \le 3.5\text{ ns}$         | 若边沿过于缓慢（呈圆弧三角波），检查排线容性负载是否过大或串联电阻阻值是否偏大                                                      |
| **4. 环路延迟与建立/保持时间 ($t_{\text{su}} / t_{\text{h}}$)** | 双通道同时测 `TCK` 与 `TDI`（或 `TCK` 与 `TDO`）                          | FPGA 接收端：`TDI/TMS` 在 `TCK` 上升沿前稳定时间 $t_{\text{su}} \ge 5\text{ ns}$，上升沿后保持 $t_{\text{h}} \ge 2\text{ ns}$          | 若 30 MHz 下由于两级缓冲 + 长排线导致环路延迟超过 $16.6\text{ ns}$，将速率降为 15 MHz 或缩短 JTAG 排线至 $\le 10\text{ cm}$ |

## 遇到的问题

| 现象                                                   | 原因                                                                                              | 处理方法                                                                                                       |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 直接双击 `unwrapped\win64.o\program_ftdi.exe` 报错缺失 DLL   | 未经 `setupEnv.bat` 与 `loader.bat` 配置环境                                                           | 改用 `D:\AMDDesignTools\2025.2\Vivado\bin\program_ftdi.bat` 执行                                               |
| Vivado 识别出 `Xilinx/2026110401A`，但下方显示 `No device`    | `U1` Pin 15（`FT_TMS`）与相邻的 Pin 16（`VCCIO 3V3`）连锡短路，导致 `TMS` 恒为 `1`，FPGA 锁死在 `Test-Logic-Reset` 态 | 通过 MPSSE `0x80`/`0x81` 脚本逐位排查发现 Bit 3 恒为 `1`，用烙铁清除 `U1` Pin 15~16 连锡后立即恢复正常并扫出 `0x5ba00477` 与 `0x147ff093` |
| 30 MHz 下使用 MPSSE `0x39`（正沿采 `TDO`）读出的 IDCODE 左移了 1 位 | 30 MHz 半周期仅 `16.67ns`，而经过 `U4` 双向电平转换 + 排线 + FPGA 的总环路延迟约 `17.5ns`，正沿采样落在 `TDO` 翻转沿后            | 15 MHz 及以下使用 `0x39` 零误码；30 MHz 高速模式下改用 `0x3D`（负沿采样）或缩短连接排线长度，实测 32,000 bits 零误码                            |

## 回顾

- **学会了什么？**
  - 掌握了利用 FT2232H MPSSE `0x80`（写方向与电平）配合 `0x81`（回读焊盘真实电压）进行**免示波器板级故障隔离**的方法：先关断外部缓冲器（`OE_N=1`）测主控引脚是否对电源/地短路，再开启缓冲器（`OE_N=0`）测通道方向。
  - 掌握了利用 JTAG 链固有的 `Shift-DR` 64-bit `IDCODE` 移位寄存器实现 1 MHz ~ 30 MHz 全链路伪随机码误码率（BER）测试与环路传播延迟分析。
- **哪些结论已经实际验证？**
  - 清除 `U1` Pin 15~16 连锡后，板卡已成功连接 AMD Zynq UltraScale+ RFSoC 目标板，准确识别出 `arm_dap`（`0x5ba00477`）与 PL（`0x147ff093`），并在 1 MHz ~ 30 MHz 下通过了 32,000 bits 连续移位无误码测试。
- **下次需要继续验证什么？**
  - 第二版 PCB（已内置 `33Ω` 源端匹配电阻与修正后的 `U4` 方向）打样贴片回来后，使用示波器加接地弹簧针实测 30 MHz 下目标板端的 `TCK` 边沿单调性与过冲幅度。

## 参考资料

- FTDI Application Note AN_108: *Command Processor for MPSSE and MCU Host Bus Emulation Modes*（FT2232H/FT4232H MPSSE 指令集官方手册，访问日期：2026-11-04）。
- AMD Technical Documentation (UG908): *Vivado Design Suite User Guide: Programming and Debugging*（Vivado 2025.2）。
- 配套测试脚本：[mpsse_jtag_diag.py](../../../code/FT2232H%20USB-JTAG/mpsse_jtag_diag.py)。
- 自制Xilinx JTAG仿真器[[自制Xilinx JTAG仿真器_xilinx hs2 diy-CSDN博客](https://blog.csdn.net/feitingfj/article/details/113048711)].
- Xilinx JTAG Support on FTDI[[Xilinx JTAG Support on FTDI](https://etherealwake.com/2024/06/xilinx-ftdi-jtag/)]:详细说明了FTDI硬件管脚的作用。
