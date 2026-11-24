# RAM part number reference

Part numbers seen while sorting, so repeat sticks can be identified quickly.

## OEM labels and the module underneath

| OEM label | Actual module | Size / type | Seen |
|---|---|---|---|
| HP 932817-672 (DIMM-CT: RGVNHGBTFB50SC) | Micron MTA8ATF1G64HZ-2G6E1 | 8GB 1Rx8 DDR4-2666 laptop SODIMM (PC4-2666V-SA2) | Nov 12, 2026: same stick, HP label on one side, Micron on the other. HP label since removed. |

## Stickerless sticks identified from chips

| Chips / board | Module | Notes |
|---|---|---|
| SK hynix H5AN8G6NAFR-UHC, 4 chips per side, SK hynix board | DDR4-2400 laptop SODIMM: 4GB 1Rx16 if one-sided, 8GB 2Rx16 if both sides have chips | Nov 12, 2026 |
| Micron FBGA D9TGG, 8 chips per side (16 total), black aftermarket PCB, inventory stickers M00420963 / M00420965 | 16GB DDR4-2666 laptop SODIMM, 2Rx8 (listed as G58) | Nov 13, 2026. Decode (MT40A1G8SA-075:E, 8Gb DDR4-2666) came from another chat; not verified against Micron's decoder. |

## Keep rule: buffered EDO DIMMs (from Terapeak, Nov 23, 2026)

Buffered EDO ECC DIMMs of **128MB or larger** sell (e.g. Sun 501-2654 128MB pairs ~$15, 2x256MB kits ~$45, Dell 4x256MB ~$58). Also keep 64MB buffered EDO with an Apple, Sun, Dell or HP label.

How to spot: 168-pin DIMM, a buffer chip in the middle (e.g. 74FCT16244 / PI74FCT16244), 18 chips (ECC), chip speed -5 or -6 (50/60ns), often 3.3V.

Size from the chips (18 chips, x4 parts):
- 16Mbit chips (4Mx4, e.g. HY51V17404, KM44C4103, MT4LC4M4): 32MB per 9 chips, so 32MB or 64MB stick: trade unless branded.
- 64Mbit chips (16Mx4, e.g. HM5165405, KM44V16104, MT4LC16M4, HY51V65404): **128MB** with 18 chips, **256MB** with 36: keep.
