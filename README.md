# NEO Piano

NEO Piano la ung dung piano cho thiet bi giao duc NEO One (ARM64/Armbian).
Ung dung su dung Python, PyQt6 va Qt Quick/QML.

Am thanh duoc tong hop boi FluidSynth va xuat truc tiep qua ALSA tren Linux.
Goi Debian tu dong cai thu vien native va SoundFont TimGM6mb gon nhe.

## Phat trien

Yeu cau Python 3.10 tro len.

Tren Fedora, cai dat bo tong hop am thanh mot lan:

```bash
sudo dnf install fluidsynth fluid-soundfont-gm
```

Goi Debian se tu dong cai cac dependency tuong duong.

```bash
python3 -m venv .venv
source .venv/bin/activate
make dev
make run
```

## Kiem tra

```bash
make test
make lint
make build
```

## Dong goi Debian 12

Can Docker hoac Podman:

```bash
make deb
```

Goi `.deb` duoc tao trong `dist/` va co the cai bang `apt` tren NEO One.

## Dieu khien va do tre am thanh

Bo 5 phim mac dinh su dung cac phim mui ten va Space. Bang dieu khien co the mo
rong thanh 8 hoac 12 phim trang. Nhan Escape de tat tat ca cac not. Cau hinh mac
dinh la 3 buffer, moi buffer 128 sample tai
48 kHz. Co the dieu chinh khi do tren NEO One bang cac bien moi truong
`NEO_PIANO_PERIOD_SIZE`, `NEO_PIANO_PERIODS`, `NEO_PIANO_SAMPLE_RATE` va
`NEO_PIANO_SOUNDFONT`.

## Cai dat tren NEO One

```bash
curl -fsSL https://raw.githubusercontent.com/lgthevinh/neo-piano/main/scripts/install_on_neo.sh | bash
```
