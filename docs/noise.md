# Noisy pixel masking

First, the mask of noisy pixels has to be determined and stored in a PNG file using the action ```NoiseDetection```:

```python
job = StackJob("job", "E:/Focus stacking/My image directory/")
job.add_action(NoiseDetection("noise-map", input_path=["src"]))
job.run()
```

Usually, this job should be run first, enabling the option ```plot_histograms```, playing with the plot range (```plot_range``` option) in order to determine the optimal threshold values (```channel_thresholds```) to be applied in order to mask a reasonable number of pixels. Once the threshold values are determined, the main focus stacking job should be ran adding the sub-action ```MaskNoise``` before ```AlignFrames``` and ```BalanceFrames```.

Arguments for the constructor of ```NoiseDetection``` are:
* ```name``` (optional, default: ```noise-map```): name of the action and default name of the subdirectory within ```working_path``` where aligned noise map is written. 
* ```input_path``` (optional): one or more subdirectory within ```working_path``` that contains input images to be combined. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where noise map is written. If not specified,  it is equal to  ```name```.
* ```working_path``` (optional): the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```max_frames``` (optional): if provided, at most ```max_frames``` images are analyzed to extract noisy pixel mask.
* ```method``` (optional, default: ```norm_lab```): if ```rgb```, noisy channel are determined.
separately on the R, G and B channel. If equal to ```norm_rgb```, the norm in the RGB color space is
used to determine noisy pixels. If equal to ```norm_lab```, the norm in the LAB color space is
used to determine noisy pixels.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the different actions.
* ```plot_histograms```  (optional, default: ```False```): if ```True```, plot a summary of the number of hot pixel by channel as a function of the applied threshold. It may be useful to set the optimal threshold values.
* ```noisy_masked_px``` (optional, default: ```(100, 100, 100)```): tentative number of noisy pixels to be masked. If set greater than zero, the threshold is computed automatically to match the desired
number of pixels to mask. If ```method```=```norm```, only the first of the three thresholds is used.
* ```channel_thresholds``` (optional, default: ```(13, 13, 13)```): threshold values for noisy pixel detections in the color channels R, G, B, respectively. Each of these thresholds is only used of the 
corresponding value in ```noisy_masked_px``` is set to zero. If ```method```=```norm```, only the
first of the three values is  used.
* ```blur_size``` (optional, default: 5): image blur amount for pixel detection.
* ```file_name``` (optional, default: ```hot_pixels.png```): noise map filename.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module. 

After the noisy pixel mask has been determined, noisy pixels are then masked adding the action ```MaskNoise``` to the ```Actions``` module:

```python
job.add_action(Actions("mask", [MaskNoise(*options)]))
```

Or as preliminary stage to more actions:
```python
job.add_action(Actions("align", [MaskNoise(),
                                 AlignFrames(),
                                 BalanceFrames(mask_size=0.9,
                                               intensity_interval={'min': 150, 'max':65385})]))
```

Note that if the number of pixels contained in the mask file (```noise_mask``` option) is greater than 1000, the job is aborted.

Arguments for the constructor of ```NoiseDetection``` are:
* ```noise_mask``` (optional, default: ```hot-rgb.png```): filename of the noise mask
*  ```kernel_size``` (optional, default: 3): blur size use to extract noisy pixels
*  ```method``` (optional, default: ```INTERPOLATE_MEAN```): possible values: ```INTERPOLATE_MEAN```, ```INTERPOLATE_MEDIAN```. Interpolate using mean or median of neighborhood pixels to replace a noisy pixel.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module. 
