# Dataset Image Fix Report

Generated 2026-08-03 from the checked-in dataset. No dataset images or labels were changed.

## Summary

- Mandatory annotation repair: 54 images (63 invalid/incompatible label lines).
- Exact duplicates: 28 duplicate pairs (28 redundant images).
- Confirmed cross-split exact duplicate: 1 pair.
- Evaluation repeated-source groups: 10 validation groups and 10 test groups.
- Low-resolution review: 38 images with a side below 256 pixels.

Resolve the mandatory annotation section first. Then rebuild train/validation/test splits by source family before training.

## 1. Mandatory annotation repair

| Split | Image | Problem | Required action |
| --- | --- | --- | --- |
| train | dataset/train/images/-2026-07-23-150427_png.rf.fb3d6dd1b6dd2eacfefda75c49efde4a.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/-2026-07-24-101104_png.rf.0e4af93d5c92a2b558cc724bc4e708df.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/-2026-07-24-101439-_png.rf.a9414bef1755c83c12f97fbd5f043ddb.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/00170-house-has-standing-water-in-the-basement-should-i-negotiate-v0-pb90a52ptihb1_jpg.rf.8fb9a6a314d569ce517dc5c1562d140c.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/0107-_jpg.rf.4d4c552b86b9dc59593c03e454828158.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/0133-_jpg.rf.bf4265b25de17f6a0bb21e89cdb6a93c.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/0210-_jpg.rf.7aa51005e9e3898dd6a28092134a65cf.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/0217-_jpg.rf.fed5417968127692b8a2d47945174806.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1649_jpg.rf.276a52764b9f10eb5723a656cfd11f18.jpg | 2 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1665_jpg.rf.bdf9878d835fd4cf2a77af839ba72018.jpg | 2 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1667_jpg.rf.2e8eb5edba8a80b466628aa4a0feb69c.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1671_jpg.rf.9730011fa80b37383813c256dd7b6c75.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1680_jpg.rf.4505a1e2650cf0c97c3f75e789dba825.jpg | 2 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1684_jpg.rf.0cc754b2294ece7025164b05aa4a0275.jpg | 3 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1696_jpg.rf.20619864a10240426311039c437e99a4.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1700_jpg.rf.d93391f6820432c6b61b90be1aac8443.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1891_jpg.rf.886f609e7a0d28720642732f5e4b857d.jpg | 2 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/1990_jpg.rf.34b683e8cfbec49bbbe9cab899e9b4aa.jpg | 2 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| train | dataset/train/images/333_mp4-13_jpg.rf.89be8eeb18b923f338a0a60e1860f97e.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/333_mp4-2_jpg.rf.1308e6662487a0bdbd2cd06d1ce95d09.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/333_mp4-3_jpg.rf.a8726a4e092a2111d87cb868f0499c0b.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/47_jpeg_jpeg_jpg.rf.eadecbf86213b73550a8eca0c050ad4c.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/52_jpg.rf.fd6d267f61be90955d40bd6a4c2d9e0d.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/60_jpg.rf.bc636e99e9969a6f73f1e825c8ae172b.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/636cfe2f0d87c_waterguard-to-ultrasump-epsom_jpg.rf.71ebc4c0fafa51ef8da3226138fc4378.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/74_mp4-22_jpg.rf.3b12898e634a8a39666cbc45a15fbece.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/753164348_1354124756786727_533446923373163865_n_jpg.rf.00bd688d68f8ffe3abf103f47d4e66d2.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/aug_istockphoto-1247005338-612x612_jpg.rf.f53fbb6ef3ec7911b2c6d795ef6e6100.jpg | 2 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/c0srq1as5d381_webp_webp.rf.e75b1953ea61877f5ff63d86c7e3edec.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/house-has-standing-water-in-the-basement-should-i-negotiate-v0-pb90a52ptihb1_jpg.rf.3feb49dfd5d50a201674f0b121554184.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-1-_jpeg_jpg.rf.b69a9e154f057d1744b38d44743c9cc0.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-10-_jpeg_jpg.rf.80994daf08e80eb4eb2f360e7a322701.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-13-_jpeg_jpeg.rf.3c4a0f0c7fe98a3c0d299b7376378194.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-20-_jpeg_jpg.rf.c30ea97586a7587af8ef58c13dd9503f.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-7-_jpeg_jpg.rf.cfa7d6e0f5d9a31532f3f7125d944e49.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-8-_jpeg_jpg.rf.cb9094f310d78bbdf0bbc3f8a82e853e.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images-9-_jpeg_jpg.rf.6ae63a2326582751496ba0cf743eb2e4.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images_jpg.rf.13fc048a4e73a1cdc3e6675e02e25b12.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images_jpg.rf.29c3c2d7aa4693d7910d042f15076cdf.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/images_jpg.rf.2c8f59a6cdb1d6fdf390b8ff63e2a707.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/Structural-Member-Cracks-and-live-water-_jpg.rf.c316047dfc6158eab6a4fe38c461bde0.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/unnamed_jpg.rf.a687400002b2dc6a58ce31a44312ddcd.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/water-17_jpg.rf.fac8db90294afeb99908eaf26e9f76e5.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/water-seeping-through-concrete-more-details-in-comments-v0-3suxc0nrb2ea1_webp_jpg.rf.692ac8b5d30848f917c1f5d2adca344e.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| train | dataset/train/images/WhatsApp-Video-2023-07-13-at-15_03_37_mp4-3_jpg.rf.efcb614100f4f336d31404e639a81502.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| valid | dataset/valid/images/014_B_-_-_jpg.rf.fc2f92d6ef1ec3e766fe0349a53aeb2e.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| valid | dataset/valid/images/0227-_jpg.rf.9d1f4edf5b56a17279934e0c21e380c5.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| valid | dataset/valid/images/1656_jpg.rf.37c8945be5fbc420dae97e856129597e.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| valid | dataset/valid/images/Basement-Water-Stains-on-Floor_png_png.rf.13c04cd8a133afc6aaeb45a98f865970.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| test | dataset/test/images/0136-_jpg.rf.091dae168e8a39dff72497792dde1aab.jpg | 1 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| test | dataset/test/images/1668_jpg.rf.9f41742b245814cba26c71927cfdb12d.jpg | 2 polygon/9-field line(s) | Convert each polygon to one tight 5-field YOLO box |
| test | dataset/test/images/74_mp4-15_jpg.rf.0299b99617852b395ad02d5254dcabfb.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| test | dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.46749232e353896929fa9f17edd1e82e.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |
| test | dataset/test/images/Dreyer_water_6-19-09_013_-12-_jpg.rf.0d9eaf838aafe3986f3e8cca27764332.jpg | 1 out-of-bounds box(es) | Visually review, then clamp coordinates inside the image |

## 2. Exact duplicate images

Compare each pair and its labels, keep the better annotation, and remove or quarantine the redundant copy. For the cross-split pair, keep only one family in one split.

| Location | Duplicate images |
| --- | --- |
| train | dataset/train/images/images-1-_jpeg_jpg.rf.a4f664973395e9a1aa8335e79692a64c.jpg<br>dataset/train/images/images-1-_jpeg_jpg.rf.f4a50e2a5fe23ef30d2a91e13d7919ad.jpg |
| train | dataset/train/images/images-12-_jpeg_jpg.rf.4315f598f5fab2e47decbf9f72608ca1.jpg<br>dataset/train/images/images-12-_jpeg_jpg.rf.9ddcf676222c1962ee87ec0c5d7994ba.jpg |
| train | dataset/train/images/images-20-_jpeg_jpg.rf.c30ea97586a7587af8ef58c13dd9503f.jpg<br>dataset/train/images/images-20-_jpeg_jpg.rf.d361c7a67b81c61cc2571bbf4367ddf6.jpg |
| train | dataset/train/images/wet-basement-floor-summer-damage-risk_webp_jpg.rf.079f0a7b185139aa6df14faf01d58dda.jpg<br>dataset/train/images/wet-basement-floor-summer-damage-risk_webp_jpg.rf.bc0d0f236361ea84947301bf1eadffa4.jpg |
| train | dataset/train/images/economical-way-to-level-this-lumpy-porch-v0-5pytld5zzajd1_webp_jpg.rf.0ecfde7de30c7c55d8b349041cb6d308.jpg<br>dataset/train/images/economical-way-to-level-this-lumpy-porch-v0-5pytld5zzajd1_webp_jpg.rf.a5f8a23ad3d34cf8597e5cf299564f61.jpg |
| valid | dataset/valid/images/1gCFDLh_jpg.rf.09daa1aab3bfb8f694d03a4f73b10a2c.jpg<br>dataset/valid/images/1gCFDLh_jpg.rf.29350d67c6ee360a746875dad570d7c5.jpg |
| train | dataset/train/images/how-to-know-if-my-frige-is-leaking-water-or-coolant-what-do-v0-DGg4DbEn5FE5dJzcCLH9mMSyJUbQmFUNcMmgYU56Inw_webp_jpg.rf.6322aa801cff8f9cb549070af7c9ed06.jpg<br>dataset/train/images/how-to-know-if-my-frige-is-leaking-water-or-coolant-what-do-v0-DGg4DbEn5FE5dJzcCLH9mMSyJUbQmFUNcMmgYU56Inw_webp_jpg.rf.b8c54fa17d5c3669f695458c7f7caf4a.jpg |
| train | dataset/train/images/house-has-standing-water-in-the-basement-should-i-negotiate-v0-pb90a52ptihb1_jpg.rf.3feb49dfd5d50a201674f0b121554184.jpg<br>dataset/train/images/house-has-standing-water-in-the-basement-should-i-negotiate-v0-pb90a52ptihb1_jpg.rf.9921176a7c1a1248b7da02ba4e10fe90.jpg |
| train | dataset/train/images/water-runoff-management-v0-kvi5z24rz2gf1_jpg.rf.15bd6019691c878fd8fe78b52657c87d.jpg<br>dataset/train/images/water-runoff-management-v0-kvi5z24rz2gf1_jpg.rf.186d2ab20cf9a5fcd5a7d658dfbade07.jpg |
| train | dataset/train/images/help-wheres-the-water-coming-from-v0-lwhitgy8camd1_webp_jpg.rf.6c107813374495ad9044b9ab44bea3d9.jpg<br>dataset/train/images/help-wheres-the-water-coming-from-v0-lwhitgy8camd1_webp_jpg.rf.b31d072051182021a59e87958bab1125.jpg |
| train | dataset/train/images/just-moved-into-house-this-pipe-was-obstructed-during-the-v0-eXNubW5oaTB5NTRjMev-xjI6JtCCeSWERpODozpXYDT4WxTdvXLr4iPv6kuK_webp_jpg.rf.79ee83da9eebccc853a57626d8b3c5ba.jpg<br>dataset/train/images/just-moved-into-house-this-pipe-was-obstructed-during-the-v0-eXNubW5oaTB5NTRjMev-xjI6JtCCeSWERpODozpXYDT4WxTdvXLr4iPv6kuK_webp_jpg.rf.85ded06891aa911a2161d6ff8cff8b23.jpg |
| train | dataset/train/images/brand-new-2-months-old-furnace-whats-going-on-here-v0-u59fzxkel54c1_webp_jpg.rf.70e5be785cbaeb3c37255f11decdeac2.jpg<br>dataset/train/images/brand-new-2-months-old-furnace-whats-going-on-here-v0-u59fzxkel54c1_webp_jpg.rf.70ec55d17dfbaed54da37d43b07f2548.jpg |
| train | dataset/train/images/oar2_jpg.rf.a7fbbad852efff4794b85bd218fbd831.jpg<br>dataset/train/images/oar2_jpg.rf.c2824e42d8e6b4a3d7c9174fd6309127.jpg |
| valid | dataset/valid/images/Basement-Water-Stains-on-Floor_png_jpg.rf.2edbad80af3e9140f8d00175e342b01e.jpg<br>dataset/valid/images/Basement-Water-Stains-on-Floor_png_jpg.rf.b3973654d2eda094428d03d732fbd8e7.jpg |
| train | dataset/train/images/images-7-_jpeg_jpg.rf.8ebd11e50c12af9e7dd6c17b528f8a53.jpg<br>dataset/train/images/images-7-_jpeg_jpg.rf.cfa7d6e0f5d9a31532f3f7125d944e49.jpg |
| CROSS-SPLIT BLOCKER | dataset/train/images/bhkjbklb-k_jpg.rf.3e58704d9dbab3593bbe5134eb188788.jpg<br>dataset/valid/images/0_jpg.rf.081c7952c33e7e2029ab9c126a5c237d.jpg |
| train | dataset/train/images/yard-drain-buried-by-hvac-crew-stormwater-in-basement-v0-ejd3bGJhZGV4cmdiMbtIhCj6TAjMlq_LM1e5FfqUdEZtDT7u6d3kcGkbdczt_webp_jpg.rf.38b7fc43ff85d761b103355beac8becd.jpg<br>dataset/train/images/yard-drain-buried-by-hvac-crew-stormwater-in-basement-v0-ejd3bGJhZGV4cmdiMbtIhCj6TAjMlq_LM1e5FfqUdEZtDT7u6d3kcGkbdczt_webp_jpg.rf.4420d124ade9188cc5733f2f17a50b2d.jpg |
| train | dataset/train/images/images-11-_jpeg_jpg.rf.6051a0e5132299fa99dbb074bf34a853.jpg<br>dataset/train/images/images-11-_jpeg_jpg.rf.853def9f4b0aaaa91a73edeb9358702a.jpg |
| test | dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.09c5da428b99382acb5e8cbc98b2d7c2.jpg<br>dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.46749232e353896929fa9f17edd1e82e.jpg |
| train | dataset/train/images/water-coming-from-small-hole-in-block-foundation-wall-v0-25gfs7ob5gec1_webp_jpg.rf.3a1a85d541c9f9695e742589f728b3df.jpg<br>dataset/train/images/water-coming-from-small-hole-in-block-foundation-wall-v0-25gfs7ob5gec1_webp_jpg.rf.6c12197b0bc4d2c0aecd9d7a3dbd66c1.jpg |
| train | dataset/train/images/water-seeping-into-garage-v0-ng9iz9q8jxmc1_jpg.rf.46692e1c49302546b4d75dd660db5a8a.jpg<br>dataset/train/images/water-seeping-into-garage-v0-ng9iz9q8jxmc1_jpg.rf.aec74f3fc728e58f93df2f589212c9f1.jpg |
| test | dataset/test/images/65824605b3225-scaled_jpg.rf.975bf8ab163389eb0a5cee7463a2481a.jpg<br>dataset/test/images/65824605b3225-scaled_jpg.rf.a98a8d239f64960926c71cf30782149d.jpg |
| train | dataset/train/images/water-around-sump-pump-v0-anacn3raawye1_webp_jpg.rf.37045e339a5ff2dce7be819d7658d087.jpg<br>dataset/train/images/water-around-sump-pump-v0-anacn3raawye1_webp_jpg.rf.6ea2f3f78251e173e37960a87573aca6.jpg |
| train | dataset/train/images/c0srq1as5d381_webp_jpg.rf.5b3c0b9ec0a8dc382f15184dc5ebdbfc.jpg<br>dataset/train/images/c0srq1as5d381_webp_jpg.rf.952e39034f88527edfb7c3e03638edf7.jpg |
| train | dataset/train/images/water-removal-in-basement_jpg.rf.7f900821acf4b13ee2f530aaa2789e94.jpg<br>dataset/train/images/water-removal-in-basement_jpg.rf.828a7ee15fc14d5540cc7646967b3f59.jpg |
| train | dataset/train/images/00152-Flooded-basement-interior-4k-2_webp_jpg.rf.103cfdbd1c15b7cd996d68b5f01a44ec.jpg<br>dataset/train/images/Flooded-basement-interior-4k-2_webp_jpg.rf.f2652e8d01c47a2ef701870659ede2a8.jpg |
| train | dataset/train/images/how-much-water-should-be-coming-from-the-white-pipe-v0-eecg7uanr4je1_webp_jpg.rf.7b1a685b4497883dfd19985c0f8032d1.jpg<br>dataset/train/images/how-much-water-should-be-coming-from-the-white-pipe-v0-eecg7uanr4je1_webp_jpg.rf.9dfc435f2a7d6a769762f1e9d84d53fc.jpg |
| train | dataset/train/images/images-13-_jpeg_jpg.rf.26c14a3e338e8cbda0476f7cbe020842.jpg<br>dataset/train/images/images-13-_jpeg_jpg.rf.b05bb8587dda86f8d136022568f0f10a.jpg |

## 3. Repeated source variants in validation and test

These files share the same pre-Roboflow source filename. Inspect each group as one source family. Keep transformations, crops, and adjacent frames in one split; evaluation should normally retain only an independent representative rather than several augmented copies.

| Split | Source family | Images |
| --- | --- | --- |
| valid | -_jpg | dataset/valid/images/-_jpg.rf.b2ca440cef88117401df7fc6c478392f.jpg<br>dataset/valid/images/-_jpg.rf.f3315444e9247002af69796acd84667a.jpg<br>dataset/valid/images/-_jpg.rf.fe42c19fca34151c90957d8764d1059e.jpg |
| valid | 0358620_jpg | dataset/valid/images/0358620_jpg.rf.a0038dc1982a9bfc6746bb71fd66381a.jpg<br>dataset/valid/images/0358620_jpg.rf.bac1c99dada3ace6fc0eaab43593917f.jpg |
| valid | 1gCFDLh_jpg | dataset/valid/images/1gCFDLh_jpg.rf.09daa1aab3bfb8f694d03a4f73b10a2c.jpg<br>dataset/valid/images/1gCFDLh_jpg.rf.29350d67c6ee360a746875dad570d7c5.jpg<br>dataset/valid/images/1gCFDLh_jpg.rf.a461c9180dc695a98a7e89c92713271d.jpg |
| valid | 406509652b8932b7b9aece52463ceb41_jpeg_jpg | dataset/valid/images/406509652b8932b7b9aece52463ceb41_jpeg_jpg.rf.2005b5683b102d2959515f220942ecb6.jpg<br>dataset/valid/images/406509652b8932b7b9aece52463ceb41_jpeg_jpg.rf.6fb180fc3ec27e9b6af2254f6c74b6d6.jpg<br>dataset/valid/images/406509652b8932b7b9aece52463ceb41_jpeg_jpg.rf.ea8c6f7641e2e9b616ebed34f8ad8424.jpg |
| valid | 83_jpg | dataset/valid/images/83_jpg.rf.32be9849a4645de4ca07d27671e2aaa8.jpg<br>dataset/valid/images/83_jpg.rf.8b8b730b051228798ec96e1bfc60f0aa.jpg<br>dataset/valid/images/83_jpg.rf.e0402bb40011a28c6d0f17ef4d2d5af5.jpg |
| valid | 88_jpg | dataset/valid/images/88_jpg.rf.03ea44d7922c7a328f4fcdf71365f25b.jpg<br>dataset/valid/images/88_jpg.rf.794beb52bbba1dd47e14a1767c272aad.jpg<br>dataset/valid/images/88_jpg.rf.a5880be88ecbab7b7815d2ed954d3920.jpg |
| valid | Basement-Water-Stains-on-Floor_png_jpg | dataset/valid/images/Basement-Water-Stains-on-Floor_png_jpg.rf.2edbad80af3e9140f8d00175e342b01e.jpg<br>dataset/valid/images/Basement-Water-Stains-on-Floor_png_jpg.rf.b3973654d2eda094428d03d732fbd8e7.jpg<br>dataset/valid/images/Basement-Water-Stains-on-Floor_png_jpg.rf.ed97a7a3129fecf8d38903a393f8a598.jpg |
| valid | Fig_44_jpg | dataset/valid/images/Fig_44_jpg.rf.542c9d4aecd3d2028e236941adb6aac8.jpg<br>dataset/valid/images/Fig_44_jpg.rf.74106ec28e898c532e407cc396ae4d42.jpg<br>dataset/valid/images/Fig_44_jpg.rf.e2bc996e5b8ab7058f4c9e3ba91a362f.jpg<br>dataset/valid/images/Fig_44_jpg.rf.f3fcb84e8987f97046fa32b446070422.jpg |
| valid | images_jpg | dataset/valid/images/images_jpg.rf.02868dd1f0d0de4c7bd957273e7551d8.jpg<br>dataset/valid/images/images_jpg.rf.06e1fbc2e675b9e02d116f32e7db853b.jpg<br>dataset/valid/images/images_jpg.rf.ff84f285ff986c8869c384becc13b8d2.jpg |
| valid | Wet-basement-Q16332_jpg | dataset/valid/images/Wet-basement-Q16332_jpg.rf.2bd4a812b65fad6c42ed0dbea025cf1a.jpg<br>dataset/valid/images/Wet-basement-Q16332_jpg.rf.4e8fa23da2976a51e23fcffe05cd86f8.jpg<br>dataset/valid/images/Wet-basement-Q16332_jpg.rf.c054faaf5daa1520eef5b836dd8654c3.jpg |
| test | 14_jpg | dataset/test/images/14_jpg.rf.6ccd5f29563314af9bca643033f38610.jpg<br>dataset/test/images/14_jpg.rf.721da9220622ef06927a6ec51592c8d5.jpg<br>dataset/test/images/14_jpg.rf.93bf834e016441d29dcdd0677c8ce57e.jpg<br>dataset/test/images/14_jpg.rf.d699c05437404c5b2ce9c4c1d5f4c01b.jpg |
| test | 5_jpg | dataset/test/images/5_jpg.rf.55f482a0eda8cc616b7ea826b6ffced5.jpg<br>dataset/test/images/5_jpg.rf.7fec4b5e9bde100318a568870e084a24.jpg<br>dataset/test/images/5_jpg.rf.eb5203816ce5133d5b42a8bc5f703b9d.jpg |
| test | 65824605b3225-scaled_jpg | dataset/test/images/65824605b3225-scaled_jpg.rf.915e6532851697209d84af85220743cb.jpg<br>dataset/test/images/65824605b3225-scaled_jpg.rf.975bf8ab163389eb0a5cee7463a2481a.jpg<br>dataset/test/images/65824605b3225-scaled_jpg.rf.a98a8d239f64960926c71cf30782149d.jpg<br>dataset/test/images/65824605b3225-scaled_jpg.rf.f8e5e592cbe8349931c81b952d45363e.jpg |
| test | 74_mp4-17_jpg | dataset/test/images/74_mp4-17_jpg.rf.4263e643dba4b63229bb69d16cbf855f.jpg<br>dataset/test/images/74_mp4-17_jpg.rf.8bbd91e42f4c49631127240c34cdc64a.jpg |
| test | Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg | dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.09c5da428b99382acb5e8cbc98b2d7c2.jpg<br>dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.46749232e353896929fa9f17edd1e82e.jpg<br>dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.bcf3769314eb122d09da64ba8d8a2bf9.jpg<br>dataset/test/images/Chicago_leaky_basement_dc99adb78c0d8dbe053a7a9746a153eb_jpg.rf.cb62325fa867237504c93fd5e450200a.jpg |
| test | Dreyer_water_6-19-09_013_-12-_jpg | dataset/test/images/Dreyer_water_6-19-09_013_-12-_jpg.rf.064d1ad26f2b60043d540c823bafd936.jpg<br>dataset/test/images/Dreyer_water_6-19-09_013_-12-_jpg.rf.0d9eaf838aafe3986f3e8cca27764332.jpg<br>dataset/test/images/Dreyer_water_6-19-09_013_-12-_jpg.rf.6f73e87313f9f1984a800789a8312084.jpg |
| test | Fig_46_jpg | dataset/test/images/Fig_46_jpg.rf.8b4ae7f6106d4bd0f105ecc1bc232c03.jpg<br>dataset/test/images/Fig_46_jpg.rf.a35da6e59720f5a3f878a87043f6b996.jpg |
| test | Fig_67_jpg | dataset/test/images/Fig_67_jpg.rf.2c99eae2545d77369eebd2655349e3b1.jpg<br>dataset/test/images/Fig_67_jpg.rf.5b71abf86fb263fcc33116eaacc63fc6.jpg |
| test | Fig_70_jpg | dataset/test/images/Fig_70_jpg.rf.2c75f0a192e79b42add8906688c8e320.jpg<br>dataset/test/images/Fig_70_jpg.rf.46e27b86c149c4ea0b23a76490a5e62b.jpg<br>dataset/test/images/Fig_70_jpg.rf.f4b49dc9f1911ad331757c235553cabd.jpg |
| test | Fig_72_jpg | dataset/test/images/Fig_72_jpg.rf.12920bb518b90d75de0b803c81a6d82a.jpg<br>dataset/test/images/Fig_72_jpg.rf.99996c2762168291a43e47aeab737180.jpg<br>dataset/test/images/Fig_72_jpg.rf.ea449e0e413aa4c946ef600d7a14ebc6.jpg |

## 4. Potential cross-split source-family collisions

This is a filename heuristic, not proof. Generic names such as images_jpg require visual comparison. Distinctive matches should be moved so the whole family occupies one split.

| Family | Splits and images |
| --- | --- |
| -_jpg | train: dataset/train/images/-_jpg.rf.4d17bc10b9868498da216e331ab2458a.jpg<br>valid: dataset/valid/images/-_jpg.rf.b2ca440cef88117401df7fc6c478392f.jpg<br>valid: dataset/valid/images/-_jpg.rf.f3315444e9247002af69796acd84667a.jpg<br>valid: dataset/valid/images/-_jpg.rf.fe42c19fca34151c90957d8764d1059e.jpg |
| 0_jpg | train: dataset/train/images/0_jpg.rf.d7f38660c6634553f51f2c3c26ccf1cf.jpg<br>valid: dataset/valid/images/0_jpg.rf.081c7952c33e7e2029ab9c126a5c237d.jpg |
| 04d339114aebf114_jpg | train: dataset/train/images/04d339114aebf114_jpg.rf.e8c94eda0f684edbc8b6f250ea65107e.jpg<br>valid: dataset/valid/images/04d339114aebf114_jpg.rf.ef0ae0bdb165c64fc371a76d302857c3.jpg |
| 0b8d6377100090f6_jpg | train: dataset/train/images/0b8d6377100090f6_jpg.rf.0a2715337f9c998124008f4619af7fa9.jpg<br>valid: dataset/valid/images/0b8d6377100090f6_jpg.rf.b4768331d9dcc5b89384156b6a806fee.jpg |
| 1_jpg | train: dataset/train/images/1_jpg.rf.1bd4cf1c9f6bf38b8ba63b905d1d6056.jpg<br>train: dataset/train/images/1_jpg.rf.9b56e607e5ac2b7867f041db3ff6b0ac.jpg<br>test: dataset/test/images/1_jpg.rf.c3b779a48b53bc05ad635b0e7d8a4811.jpg |
| 12_jpg | train: dataset/train/images/12_jpg.rf.85072a7d7e450f335fec191a74dbbae5.jpg<br>valid: dataset/valid/images/12_jpg.rf.5a5a269a0fd04c8705c799e0596f0633.jpg |
| 13_jpg | train: dataset/train/images/13_jpg.rf.88fc8d9c8f43fce2b27eef90c6a3544a.jpg<br>valid: dataset/valid/images/13_jpg.rf.b4656c3b5a90747b118e95405198512d.jpg |
| 14_jpg | valid: dataset/valid/images/14_jpg.rf.96c5d776bdc5a42acb46121a66a090b8.jpg<br>test: dataset/test/images/14_jpg.rf.6ccd5f29563314af9bca643033f38610.jpg<br>test: dataset/test/images/14_jpg.rf.721da9220622ef06927a6ec51592c8d5.jpg<br>test: dataset/test/images/14_jpg.rf.93bf834e016441d29dcdd0677c8ce57e.jpg<br>test: dataset/test/images/14_jpg.rf.d699c05437404c5b2ce9c4c1d5f4c01b.jpg |
| 17_jpg | train: dataset/train/images/17_jpg.rf.a501569c877ab73282225d72dfade0e6.jpg<br>train: dataset/train/images/17_jpg.rf.fb02679fccdd96b0cda94ab81d5967ff.jpg<br>test: dataset/test/images/17_jpg.rf.f197f3e1903b9ec509373ffc54773d56.jpg |
| 18_jpg | train: dataset/train/images/18_jpg.rf.11b8724ff4961e6fe0af1b96e37cb5fc.jpg<br>valid: dataset/valid/images/18_jpg.rf.9dda2ea45694cd6febedeef95b8bc5c6.jpg |
| 24_jpg | train: dataset/train/images/24_jpg.rf.2e37d2a9b639d7c19f3144c52038a825.jpg<br>train: dataset/train/images/24_jpg.rf.44291894a4c7b3c3b5e71773bf3c7ab9.jpg<br>train: dataset/train/images/24_jpg.rf.5e29fb66398edba9176d4569e11ac244.jpg<br>test: dataset/test/images/24_jpg.rf.2680b5b6f37b7127cdd434304b914c7a.jpg |
| 29_jpg | train: dataset/train/images/29_jpg.rf.72155633da5325e58aa324d344d85336.jpg<br>train: dataset/train/images/29_jpg.rf.811c4e2bf2262f15e14bce1977d35b5c.jpg<br>test: dataset/test/images/29_jpg.rf.b07cf47e067ea0b8c4bb25d365b164de.jpg |
| 30_jpg | valid: dataset/valid/images/30_jpg.rf.07f7ce1cf5fb039158a205b9a271254e.jpg<br>test: dataset/test/images/30_jpg.rf.3efb76f61de5216f195ca4b4ade29cf6.jpg |
| 5_jpg | train: dataset/train/images/5_jpg.rf.fd21bfaafbb3c4bb4c826289858711c8.jpg<br>valid: dataset/valid/images/5_jpg.rf.3da3c3a8eb7bf049ea511ee11c3c0fb2.jpg<br>test: dataset/test/images/5_jpg.rf.55f482a0eda8cc616b7ea826b6ffced5.jpg<br>test: dataset/test/images/5_jpg.rf.7fec4b5e9bde100318a568870e084a24.jpg<br>test: dataset/test/images/5_jpg.rf.eb5203816ce5133d5b42a8bc5f703b9d.jpg |
| 7_jpg | train: dataset/train/images/7_jpg.rf.3579a03c3ade540ea245297e8f3ed024.jpg<br>valid: dataset/valid/images/7_jpg.rf.78885f49e8d79bac8bb99a954208c6d2.jpg |
| Image_10_jpg | train: dataset/train/images/Image_10_jpg.rf.59b4fbdbc1bc954bf047922cd7632888.jpg<br>valid: dataset/valid/images/Image_10_jpg.rf.464fb94a9cb1a570409834bcd5895b59.jpg |
| Image_100_jpg | train: dataset/train/images/Image_100_jpg.rf.162d4e9701474a2204acb3638dc424e3.jpg<br>valid: dataset/valid/images/Image_100_jpg.rf.24f185372b88ea9f86b5369747fe42b8.jpg |
| images_jpg | train: dataset/train/images/images_jpg.rf.06bc20453f5f0944a2c6b5187034c0a8.jpg<br>train: dataset/train/images/images_jpg.rf.12d8ec25904bf90acc66374a1bd29702.jpg<br>train: dataset/train/images/images_jpg.rf.13fc048a4e73a1cdc3e6675e02e25b12.jpg<br>train: dataset/train/images/images_jpg.rf.174a6005024cdcc9d37cabce9267808e.jpg<br>train: dataset/train/images/images_jpg.rf.25038234cab3a0479f23da0d04118278.jpg<br>train: dataset/train/images/images_jpg.rf.266222f9ba4cd07449afe80ff270d261.jpg<br>train: dataset/train/images/images_jpg.rf.29c3c2d7aa4693d7910d042f15076cdf.jpg<br>train: dataset/train/images/images_jpg.rf.2c8f59a6cdb1d6fdf390b8ff63e2a707.jpg<br>train: dataset/train/images/images_jpg.rf.472e743698ee0c3f7513fa81d68cca94.jpg<br>train: dataset/train/images/images_jpg.rf.4d2460d67e144903e1491c96ac7b34d5.jpg<br>train: dataset/train/images/images_jpg.rf.62cb2f33c380de4e7e62b3cbeb1f4fb5.jpg<br>train: dataset/train/images/images_jpg.rf.73ca6d609c3f0656042f351308293baf.jpg<br>train: dataset/train/images/images_jpg.rf.763dc29b9f920fde5c347bd9787612fc.jpg<br>train: dataset/train/images/images_jpg.rf.7c8cdd136440bba888ffc34a445ccb88.jpg<br>train: dataset/train/images/images_jpg.rf.7cfe815bd4cd36cb2c6fe0c3fe44a7a3.jpg<br>train: dataset/train/images/images_jpg.rf.83e6ee999b5f0c2821a51169c4d51e36.jpg<br>train: dataset/train/images/images_jpg.rf.8542d9be1380660d1b314ee5d5f92107.jpg<br>train: dataset/train/images/images_jpg.rf.9207fd947e0972db6125bda08f6610d2.jpg<br>train: dataset/train/images/images_jpg.rf.9f8524c171e9686c7ecfc5a258ee6f6f.jpg<br>train: dataset/train/images/images_jpg.rf.a5645fd0bdbc4004b97a3d5f48d019eb.jpg<br>train: dataset/train/images/images_jpg.rf.a88553b9563bfa0a4665ff5dafda3c19.jpg<br>train: dataset/train/images/images_jpg.rf.a8ed880a9cf540828f5f3b51b4dc0647.jpg<br>train: dataset/train/images/images_jpg.rf.a9e54790a5b75936d8b9676dfaf33278.jpg<br>train: dataset/train/images/images_jpg.rf.aa160c79d1e8129d55fdd54c6c9c8695.jpg<br>train: dataset/train/images/images_jpg.rf.c5790ca0e65ddb1ba2608b73434e897b.jpg<br>train: dataset/train/images/images_jpg.rf.c5fa5875d94b71c7d5abf9fbdaae8698.jpg<br>train: dataset/train/images/images_jpg.rf.cefbbd4c14110214c063a3de29377523.jpg<br>train: dataset/train/images/images_jpg.rf.d473d6a77e149ca719801ca70b5e28de.jpg<br>train: dataset/train/images/images_jpg.rf.ec72315da3b896ee8446e08fae9b0164.jpg<br>train: dataset/train/images/images_jpg.rf.f610c73712dc014a451add93807ce4d5.jpg<br>train: dataset/train/images/images_jpg.rf.fb54a827c3a40127b641da7ea56cf4b5.jpg<br>valid: dataset/valid/images/images_jpg.rf.02868dd1f0d0de4c7bd957273e7551d8.jpg<br>valid: dataset/valid/images/images_jpg.rf.06e1fbc2e675b9e02d116f32e7db853b.jpg<br>valid: dataset/valid/images/images_jpg.rf.ff84f285ff986c8869c384becc13b8d2.jpg |
| jpg | train: dataset/train/images/aug_1018_43d338_jpg.rf.dd3828a049c2c21c3892464f3d591713.jpg<br>train: dataset/train/images/aug_104_441b75_jpg.rf.ff69fba4200eed3a99765f94a41ce699.jpg<br>train: dataset/train/images/aug_131_536589_jpg.rf.6682b156e035fe080b553d47cfbb2dcb.jpg<br>train: dataset/train/images/aug_20_cc9ba3_jpg.rf.b8fa7485975d563436ffe2e0486bbeba.jpg<br>train: dataset/train/images/aug_243_7139a1_jpg.rf.3638cb34de4a720b473e0b7789248511.jpg<br>train: dataset/train/images/aug_252_86c20d_jpg.rf.a0b899209f39af24f6b59fb2c5dc0365.jpg<br>train: dataset/train/images/aug_264_ced459_jpg.rf.d284e2b8459cc2a4c61de061d35fb574.jpg<br>train: dataset/train/images/aug_268_42e5c5_jpg.rf.00d5347b0230c5ee74815e02f8853c59.jpg<br>train: dataset/train/images/aug_286_d3bf77_jpg.rf.39ae689d103c735d0f57351fd6d4ccf2.jpg<br>train: dataset/train/images/aug_300_05d669_jpg.rf.3fd3b05818ce47d35c98132c2e47c401.jpg<br>train: dataset/train/images/aug_381_fe24b8_jpg.rf.19f715fc245b280d76dbb40bc2fb04e0.jpg<br>train: dataset/train/images/aug_466_b46286_jpg.rf.8d192390359f3517850f90789b176abd.jpg<br>train: dataset/train/images/aug_488_9f6faf_jpg.rf.86fe37cf60f6938666d021a14dca285d.jpg<br>train: dataset/train/images/aug_771_515461_jpg.rf.3412c672fdce5cda644eca8b273cf074.jpg<br>train: dataset/train/images/aug_773_f2f2cd_jpg.rf.9a34196e01a8202965e0450a762dd433.jpg<br>train: dataset/train/images/aug_77_618e77_jpg.rf.b6ab92b50fa9acad7e4d3ab2d37ec20a.jpg<br>train: dataset/train/images/aug_780_5c0b14_jpg.rf.45a5b2434d5476e50e61b701816de3d2.jpg<br>train: dataset/train/images/aug_919_8dd87c_jpg.rf.ff55a4eb75768cc656e8de6144ac2b06.jpg<br>train: dataset/train/images/aug_99_077d5e_jpg.rf.5aeb8e690b39f595091cc9935078486e.jpg<br>valid: dataset/valid/images/aug_181_afa2a3_jpg.rf.3caf2b1085bc481fce31b9697b94338b.jpg<br>valid: dataset/valid/images/aug_187_52b241_jpg.rf.75fd07150847a7727eb4d75672843fe1.jpg<br>valid: dataset/valid/images/aug_274_ca593e_jpg.rf.c82efdc9172cf010d9c67c13d5e21d58.jpg<br>test: dataset/test/images/aug_124_2dd9f6_jpg.rf.9a7fc4e65c03636acc29acddebf0eb26.jpg<br>test: dataset/test/images/aug_178_9b5728_jpg.rf.a4bed57e6f18fa99596071caace165c5.jpg<br>test: dataset/test/images/aug_38_304c7c_jpg.rf.8699ff807c4669432225025be87b9e2b.jpg<br>test: dataset/test/images/aug_76_c28234_jpg.rf.ae4c5b352ec809644f0e38eca745d96e.jpg |

## 5. Low-resolution images to review or replace

These images have at least one side below 256 pixels. They are not automatically invalid, but they are poor candidates for tiny-droplet detection. Replace them with higher-resolution originals when possible; otherwise inspect whether the target remains identifiable.

| Split | Dimensions | Image |
| --- | ---: | --- |
| train | 259x194 | dataset/train/images/00227-images-4-_jpeg_jpeg_jpg.rf.0630ca37aa849aa65b364cb5de06c36b.jpg |
| train | 300x168 | dataset/train/images/00247-images-9-_jpg.rf.b0d99457836fd2a3aa9e185473bfe79e.jpg |
| train | 600x253 | dataset/train/images/17_jpg.rf.fb02679fccdd96b0cda94ab81d5967ff.jpg |
| train | 280x210 | dataset/train/images/21069935_jpg.rf.9d82e9794971cc9409e61d92bf2f96b1.jpg |
| train | 365x138 | dataset/train/images/download-4-_jpg.rf.2ba0869b0e4a29dd3c50c10a50f074b2.jpg |
| train | 262x192 | dataset/train/images/download_jpg.rf.1a257337314b58bd20ba73177facead3.jpg |
| train | 262x192 | dataset/train/images/download_jpg.rf.7a9e01292f078f864220082ce4788b57.jpg |
| train | 275x183 | dataset/train/images/download_jpg.rf.a7ff552c84f6362f27a689f3b1364658.jpg |
| train | 300x212 | dataset/train/images/ECA-News-Gas-transmission-in-Israel-300x212_jpg_jpeg_jpg.rf.7bb569982477105c095f73498dfcce4d.jpg |
| train | 313x209 | dataset/train/images/fd602203dcec55fd_jpg.rf.c768c0b17b2b41b92a60a5cb0196cafc.jpg |
| train | 225x225 | dataset/train/images/i29_jpg.rf.dced21a9ea2c482cdb63d6fe9191bd64.jpg |
| train | 335x150 | dataset/train/images/Image-303_jpeg_jpeg_jpeg.rf.a3f18d6c3bc64860666051da95ddbbf5.jpg |
| train | 275x183 | dataset/train/images/Image-305_jpeg_jpeg_jpeg.rf.6a9d63ccfcab5e10bfd15e5c58713d19.jpg |
| train | 194x259 | dataset/train/images/Image-4_jpeg_jpeg_jpeg.rf.baf0dcaa46a6a9f3335a5ae2ec694771.jpg |
| train | 260x194 | dataset/train/images/images-1-_jpg.rf.20a3c49dcd22a075734ab7e4a2928a63.jpg |
| train | 259x194 | dataset/train/images/images-13-_jpeg_jpeg.rf.3c4a0f0c7fe98a3c0d299b7376378194.jpg |
| train | 300x168 | dataset/train/images/images-18-_jpg.rf.02610ddb576c1cd4a3dee3b249fae396.jpg |
| train | 225x225 | dataset/train/images/images-2-_jpeg_jpeg.rf.813bd3e9a2c766a9668fede1a38df770.jpg |
| train | 259x194 | dataset/train/images/images-2-_jpeg_jpeg.rf.f015058ded27f40ee1f5f5a40414718c.jpg |
| train | 194x259 | dataset/train/images/images-20-_jpeg_jpeg.rf.d80f1cf85a4c20aa73c3cbebeddadac3.jpg |
| train | 275x183 | dataset/train/images/images-21-_jpeg_jpg.rf.36e7fa0879f8b65393071bac35ac2777.jpg |
| train | 259x194 | dataset/train/images/images-4-_jpeg_jpeg.rf.13e28352518a2281ff2ae0952d428c63.jpg |
| train | 194x259 | dataset/train/images/images-4-_jpeg_jpeg.rf.efb6cb155bf56a4289469695aac325f8.jpg |
| train | 253x200 | dataset/train/images/images-6-_jpeg_jpeg.rf.e774aa360043f17f3ba92a913f61eae9.jpg |
| train | 194x259 | dataset/train/images/images-6-_jpg.rf.0b49b12ae9b0e87a196c31ebdc04d61f.jpg |
| train | 408x124 | dataset/train/images/images-9-_jpeg_jpg.rf.6ae63a2326582751496ba0cf743eb2e4.jpg |
| train | 300x168 | dataset/train/images/images-9-_jpg.rf.00ec9a5c59f26384da1af0851c69fc86.jpg |
| train | 259x194 | dataset/train/images/images_jpeg_jpeg.rf.4066e7aec06888120120b853305b263c.jpg |
| train | 294x171 | dataset/train/images/images_jpg.rf.06bc20453f5f0944a2c6b5187034c0a8.jpg |
| train | 200x320 | dataset/train/images/i_103_jpeg_jpg.rf.8c9c7395d41eb8be5115417e18fc7490.jpg |
| train | 213x320 | dataset/train/images/i_108_jpeg_jpg.rf.55489b44cb3a2361363ceff1fb0c6e60.jpg |
| train | 150x200 | dataset/train/images/thumb-4-_jpg.rf.ec5c05546424361bd1db9e88924983be.jpg |
| train | 272x185 | dataset/train/images/water-17_jpg.rf.fac8db90294afeb99908eaf26e9f76e5.jpg |
| valid | 259x195 | dataset/valid/images/88_jpg.rf.03ea44d7922c7a328f4fcdf71365f25b.jpg |
| valid | 259x195 | dataset/valid/images/88_jpg.rf.794beb52bbba1dd47e14a1767c272aad.jpg |
| valid | 259x195 | dataset/valid/images/88_jpg.rf.a5880be88ecbab7b7815d2ed954d3920.jpg |
| valid | 300x168 | dataset/valid/images/i14_jpg.rf.4e0d6e607c3fd932a5704fb2852e8594.jpg |
| valid | 194x259 | dataset/valid/images/images-12-_jpeg_jpeg.rf.01de71cbd69b00ab669d7300c6156b29.jpg |

## Completion check

After repairing and resplitting, run:

    python scripts/audit_dataset.py

Do not start the final training run until the audit completes and reports no structural errors or exact duplicates.
