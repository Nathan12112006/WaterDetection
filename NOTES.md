The initial run gave poor results. This was due to bad and inconsistent box drawing. As a result, the best precision score was around 0.8, while the best recall and mAP50 scores were around 0.7.

To fix this, I went through the testing pictures and fixed many labels. I then added many null pictures to the dataset to broaden the perspective of the model. 

After running this, I was able to get the model score much higher. However, there was still a problem that I had not yet addressed: the validation batch was too similar to the training batch. Therefore, I had CODEX switch the pictures around in the already uploaded dataset to ensure that the images in the validation folder were not also in training. This ensured that the scores were not inflated by similar validation photos.

As I expected, the scores turned out to be much lower. Even though the model occasionally missed boxes, the main issue that I saw was that the model kept returning images with multiple boxes in the same location. After doing some research on this problem, I went back to my dataset and went through every picture one by one to ensure that my boxes were tight and consistent. Then I changed the IoU constraint to 0.5. This run returned the most consistent results across the three categories, and through the validation batches, I was visibly able to see the improvement. The best epoch reached 0.5533 for mAP50-95 and over 0.8 for precision, recall and mAP-50.

In an attempt to improve the results even more, I added more photos. I also increased the number of epochs, as it seemed that the model had more room to learn. This did not help.

I now start training from "best.pt" instead of starting from "yolov8n.pt". I also tightened all my boxes again before running the dataset again. I switched the number of epochs back to 50, as increasing it did not help much. 

I found out that when CODEX switch the image splits around, it messed up some of the image orientations, so the boxes were no longer in the correct location. Therefore, I had to run the command again and specifically pointed out the problem and told CODEX to fix it. I also asked CODEX to look for images that are too similar and remove one of them.

I realized that my images were too broad. I treated too many things as one class, so I removed the mold only pictures and kepts that ones that involved water leaks.

The final best results are: Precision: 0.98971, Recall: 0.70833, mAP-50: 0.81316, and mAP-50-95: 0.47713. This means that the model is able to find the correct water damage area, but struggles to draw the tight box around the area. Recall is also kind of low, so the confidence can be set to 0.1 for more detections. I believe the the biggest thing holding these results back is lack of quantity of images. I have about 550 in total, 10% of which are null images. To produce better results, I definitely need more high quality images.

After adding about 20-30 more images, I was able to get Precision: 0.90458, Recall: 0.75842, mAP-50: 0.78067, and mAP-50-95: 0.54167. Though mAP-50-95 didn't seem to improve too much, I was still able to see a massive improvement in the box drawing skills. However, after running tests myself, somehow the previous model still seems to be doing better.

I am now adding two more classes. The three classes are now water accumulation (water damage), pipe burst, and water drop. As a result I have to gather more images for my dataset. My initial run was not as good as I did not go through the images and fix the drawings. After seeing the poor results, I went through all the images, including the ones from before, to make sure my boxes are consistent and do not miss anything. Instead of labeling the water bursting out the pipe, I label the exit point (where the water bursts out from). This way the boxes can be more consistent and not take up the whole picture. Also, I increase the training image size from 640 to 960. This way, the model is able to see the smaller water drop boxes better during training. 

For the water drop boxes, I only label the clear and relatively big drop that are in the air and those that are about to drip off. I did not label the ones just sitting on a surface and also avoided the really small ones. This keeps the boxes more consistent. However, I do struggle with determining whether or not a water drop is big enough to be labeled. This may be an issue. 

For the next run, I gathered about 1100 images in total and reviewed all of them. The model show some improvement, but not a lot. 

I went through the images again and fixed all the malformed photos. I also deleted all exact duplicates and added even more images. There are now about 1200 in total. I will run this again to see if anything improves. This did improve the results a little, but not much.

I am switching my labeling methods, I will be labeling the water jet stream along with the pipe burst location and considering that as the pipe burst class. Once again, the improvement is quite small. I will not be trying to switch to the yolov26 model instead, to see if that makes a difference. I am also labeling the puddles in the pipe burst images as water accumulation. The results were better, but not by too much

I will try to switch to yolov26. I will start off with 30 epochs and compare it with the results from yolov8 to see which one is better. I have also switched the image size to 768px to reduce training time. I will see if this will actually effect the accuracy.

Running yolov26 produced much better results. However, I did not run enough epochs. For the next run, I added more images of pipe bursts and water drops. I will start the training from best.pt as well.

Instead of running the models from scratch, I have shifted to fine tuning the models. Every run I would add about 20-30 new images and start the run from the current best best.pt. I would only run this for about 30 epochs as fine tuning does not need more than that. Everytime this fine tuning would only help a little, and I am running out of images to add.

I will try to use the yolo26s model to see if that one will be better. The training will take much longer though.