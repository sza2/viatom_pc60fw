# viatom_pc60fw

Python script to read values from Viatom Wellue PC-60FW Fingertip Oximeter with Bluetooth

## BLE characteristics

The device uses [Nordic UART Service](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/include/bluetooth/services/nus.html). Actually, to read the values only the TX characteristic (Notify) is needed. I'm not sure if the RX characteristic is in use at all.

## Packet format

A packet starts with a sync word `[0xaa, 0x55]`. That's followed by `0x0f` or `0xf0` - I don't know its function. The next byte is the length of the payload including the CRC at the end of the packet. The remaining bytes are the payload and a one-byte Maxim CRC8 checksum.

I encountered four types of payloads (CRC is removed from the end):

### Numerical data: SpO2, Pulse rate, Perfusion index

Example:

| 0x0f |  0x08 | 0x01 | 0x60 | 0x3e | 0x00 | 0x50 | 0x00 | 0xc0 |
|:----:|:-----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
|   ?  | Length| Func | SpO2 |  PR  |   ?  |  PI  |   ?  |   ?  |

### Waveform data: Pulse waveform

Example:

| 0x0f |  0x07 | 0x02 | 0x3b | 0x38 | 0x35 | 0x32 | 0x2f |
|:----:|:-----:|:----:|:----:|:----:|:----:|:----:|:----:|
|   ?  | Length| Func |  WF  |  WF  |  WF  |  WF  |  WF  |

Interestingly, there is a "spike" in every pulse cycle, and it is always the third sample after the peak value of the pulse waveform. It seems to subtract 0x80 (128) from this spike value the resulting value just fits into the curve values. The maximum value of the waveform is 0x7f (except in the case of the spike) so, subtract 0x80 from the spike value doesn't seem to cause any problem.

### Unknown

Example:

| 0x0f |  0x06 | 0x21 | 0x02 | 0x00 | 0x00 | 0x00 |
|:----:|:-----:|:----:|:----:|:----:|:----:|:----:|
|   ?  | Length| Func |   ?  |   ?  |   ?  |   ?  |

### Unknown

Example:

| 0xf0 |  0x03 | 0x03 | 0x03 |
|:----:|:-----:|:----:|:----:|
|   ?  | Length| Func |   ?  |
