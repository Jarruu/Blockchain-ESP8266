# Output Pengujian

Folder ini menyimpan bukti pengujian untuk lampiran laporan.

| File | Isi | Cara menghasilkan |
|---|---|---|
| `benchmark.md` | Tabel waktu mining & konsensus | `python benchmark.py` |
| `pytest.txt` | Output unit test + integrasi | `python -m pytest -v > docs/bukti/pytest.txt` |
| `serial_esp.txt` | Salinan Serial Monitor ESP8266 | Copy-paste dari Arduino IDE |
| `wokwi_*.png` | Screenshot LCD 4 node Wokwi | Screenshot tab simulator VS Code |
