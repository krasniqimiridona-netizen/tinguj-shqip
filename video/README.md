# 💔 Lamtumira e fundit: film i shkurtër kinematografik për Instagram

Video vertikale **1080×1920, 34 sekonda, 30 fps, me muzikë**, gati për Instagram Reels / TikTok.

📁 Skedari: `video/lamtumira_e_fundit.mp4`

## Kuadrot

| Koha | Kuadri | Çfarë ndodh |
|------|--------|-------------|
| 0–3s | Titulli | *LAMTUMIRA E FUNDIT*, "shikoje deri në fund…" |
| 3–8s | Plan i gjerë, kamera afrohet ngadalë | Çifti nën llambë, në shi, të kapur për dore. *"— A më do akoma?"* |
| 8–11.6s | Plan i afërt i fytyrave | *"— …Nuk e di më."* Ajo ul kokën dhe zemra mbi ta çahet në dysh (me goditje zanore). |
| 11.6–14s | Plan i afërt i duarve | Drita dridhet, duart ndahen, ata kthejnë shpinën. *"Disa heshtje flasin më shumë se fjalët."* |
| 14–23s | Plan i gjerë, kamera largohet | Ecin në drejtime të kundërta, shiu shtohet. *"Ai zgjodhi krenarinë." / "Ajo zgjodhi veten."* |
| 23–25.6s | Plan i afërt mbi të | Ajo ndalet dhe kthehet të shikojë. |
| 25.6–28s | Plan i gjerë | Ai po zhduket. *"Ajo u kthye të shikonte… ai jo."* |
| 28–34s | Fundi | *"Disa njerëz janë kapituj, jo e gjithë historia."* + "Shëno dikë që duhet ta shohë këtë." |

Stili: shirita kinemaje, sfond i turbullt me drita bokeh, dritë kontre nga llamba mbi silueta, reflektime në rrugën e lagur, mjegull, shi në dy plane, ngjyrim filmi (hije të ftohta, drita të ngrohta) dhe grimcë filmi. Muzika është piano me harqe (strings), me ngritje dramatike para ndarjes.

## Përshkrimi për postim (copy-paste)

```
Ajo u kthye të shikonte… ai jo. 💔

Disa njerëz hyjnë në jetën tonë si kapituj, jo si e gjithë historia.

Shëno dikë që duhet ta shohë këtë 👇
Po ti, do ishe kthyer? 🤍

#shqip #dashuri #ndarje #zemerthyer #lamtumira #shqiperia #kosova #tirana #prishtina #reels #reelsshqip #viral #fyp #explore #love #breakup #heartbreak #sad #kuote #thenieshqip
```

## Këshilla që të bëhet viral

1. **Posto si Reel** (jo si postim të zakonshëm), mes orës **19:00–22:00**.
2. Në Instagram mund të shtosh edhe një **këngë trendi të trishtë** mbi muzikën origjinale (ul volumin e audios origjinale).
3. Zgjidh si **cover** kuadrin me zemrën e çarë (rreth sekondës 11).
4. Përgjigju komenteve në orën e parë, sepse kjo e shtyn algoritmin.
5. Pyetja në fund ("Po ti, do ishe kthyer?") nxit komentet.

## Ta ndryshosh ose ta rikrijosh

Tekstet janë te lista `CAPTIONS` në `krijo_video.py`. Ndryshoji dhe ekzekuto:

```bash
python3 video/krijo_video.py
```

Për të parë vetëm disa kuadro si PNG (pa krijuar videon):

```bash
PREVIEW=6,11,24 PREVIEW_DIR=/tmp/kuadro python3 video/krijo_video.py
```

Duhen: Python 3, `numpy`, `Pillow`, `ffmpeg`.
