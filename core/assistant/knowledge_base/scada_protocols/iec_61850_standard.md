# Standard IEC 61850 dan Sinkronisasi Masa

Standard IEC 61850 menetapkan protokol penghantaran data berkelajuan tinggi untuk perkakasan substesen.
Logik Nodes:
- XCBR: Pemutus litar (Breaker Control).
- MMXU: Pengukuran Voltan/Arus (Analog Metering).
- CSWI: Pensuisan logik.
Sinkronisasi Jam:
PTP (IEEE 1588) digunakan untuk penyelarasan jam dengan toleransi hanyutan maksimum 25ms. Sebarang hanyutan jam melebihi 25ms disifatkan sebagai anomali sync skew.