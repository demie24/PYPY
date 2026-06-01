# Garis Panduan Keselamatan Siber Grid Pintar (Mitigasi FDIA)

False Data Injection Attack (FDIA) disasarkan untuk menipu HMI SCADA dengan menyuntik voltan bias palsu.
Langkah Mitigasi:
1. Aktifkan penapisan adaptif berasaskan KCL/KVL physical validation.
2. Sekiranya trust score jatuh di bawah 40%, tolak data telemetri berkaitan dan kekalkan LKG (Last-Known-Good).
3. Laksanakan sekatan automasi (FLISR lockout) untuk menghalang penyerang memanipulasi pemutus litar secara automatik.