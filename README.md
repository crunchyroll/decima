"Decima" - Human Visual Quality Assessment System (HVQAS)

Dependency list: (MacOS or Linux)

- Home Brew for MacOS
  xcode-select --install
  /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

- ffmpeg with libvpx and libx264 support
  brew install ffmpeg --with-theora --with-srt --with-libvpx \
	--with-openssl --with-fdk-aac --with-fontconfig --with-freetype --with-fontconfig --with-libass

- mediainfo
  brew install mediainfo

- Python TKinter package
  should come with brew's python

- Python 2.7/3 homebrew version
  brew install python

- MPV media player
  brew install mpv

- gnuplot
  brew install gnuplot

- Bino player (side by side mode)
  http://devernay.free.fr/hacks/bino/Bino-1.6.6-OSX-Mavericks-GPL.zip

# setup system, clip mezz from remote URL, create test media clips
```
Execute the setup script:

./test/setup_svq_tests.sh <basedir> <testset>

Where <basedir> is where the tasks directory is at, default is ./tasks
yet you can specify /data/ for example and the tasks in /data/tasks/{tests}/task.json
will be setup. <testset> could be yet another level within /data/tasks/{testset}/{tests}/task.json.
{tests} are directories with task.json files with instructions for mezzanine source
, clip in point + duration and encode tests to run upon the clip point(s).

The ./tasks/ directory has some examples that will pull from the Netflix
test sources via http when you run the setup script. This will take some
bandwidth and then run the encoding on the local system using those
test sources with some test encoding variants.

The script will inform you of deps your missing and how to
get them for your system.

This will download the clip section from the mezz for each
test in the tasks/ directory which has an example test setup.

Running the setup script multiple times is safe and the tests
can be ran through via running it or individual ones using
this command when in the task ID directory.

Execute the tests:
  manually:
	./create_task.py --task_file tasks/{ID}/task.json --runtests
  script:
        ./test/run_svq_tests.sh <basedir> <testset>
```

#
# Test Modes (scope type ones used to analyze the tests objectively easier)
#
1. Side by Side: play mezzanine on left, encode on right using Bino player
2. Overlay: blend videos together, can alter blend filters mode from overlay via cmdline
3. DSIS: Double Stimulus Impairment Scale ITU test, play mezzanine then play encode
4. Difference: Use negate filter and show only differences between mezzanine and encode
5. PIP: Difference with PIP display in middle of encode + PSNR display and timecode

#
# Graph parser (executed by create_task.py)
#
There are .csv stats files created and .gp gnuplot graph configs
per test per user which can be grouped together into single graphs
using the parse_results.py script.

The MSU / ITU format is followed in CSV format:
---
CLIP_101_00-10-00_00-00-15_USER.csv
---
```
number of tests, 3
number of videos, 4
reference video, C:\videos\CLIP_101_00-10-00_00-00-15_mezz.mov
video, mark
C:\videos\CLIP_101_00-10-00_00-00-15_vp9.webm,5,
C:\videos\CLIP_101_00-10-00_00-00-15_crf.mp4,5,
C:\videos\CLIP_101_00-10-00_00-00-15_abr.mp4,4,

Screen resolution, width, 1920, height, 1080,

time of assessment, 00:00 10/09/2018,
```
---

One users results only:
./parse_results.py --csv_dir ./tasks --csv_file "*_ckennedy.csv" --out_file ckennedy

All users results:
./parse_results.py --csv_dir ./tasks --csv_file "*.csv" --out_file ckennedy

#
# How to use create_task.py
#
Graphs can be displayed with results after each test for feedback purposes.
 add --showresults

```
optional arguments:
  -h, --help            show this help message and exit
  --hash_id hash_id     Hash ID
  --username username   Username of tester
  --tasks_file tasks_file
                        Tasks file
  --mezzanine_file mezzanine_file
                        Mezzanine to use
  --output_dir output_dir
                        Output directory path for encodes
  --debug               Debug
  --dryrun              Dryrun
  --runtests            Runtests
  --showresults         show result graphs
  --rawyuv              Create raw YUV video too
  --bino                Use Bino for side by side playback
  --sidebyside          Show video side by side
  --sidebysidemode sidebysidemode
                        mode to use for Bino output display using -o
  --overlay             Show mezzanine with encode overlay video
  --blendmode blendmode
                        Blend mode to use for libav blend filter
  --overlaymode overlaymode
                        Overlay mode to use for libav overlay mode (blend or
                        difference)
  --mezz_alpha mezz_alpha
                        Alpha channel transparency level of mezzanine (0.9 by
                        default)
  --enc_alpha enc_alpha
                        Alpha channel transparency level of encode 0.6 by
                        default)
  --creategraphs        create graphs after tests are ran
  --ffmpeg_options ffmpeg_options
                        extra options for ffmpeg
```

---
side by side Bino modes (--bino --sidebysidemode):
https://bino3d.org/doc/bino.html#Output-Techniques
---
```
stereo                   OpenGL stereo
alternating              Left/right alternating
mono-left                Left view
mono-right               Right view
top-bottom               Top/bottom
top-bottom-half          Top/bottom, half height
left-right               Left/right
left-right-half          Left/right, half width
even-odd-rows            Even/odd rows
even-odd-columns         Even/odd columns
checkerboard             Checkerboard pattern
hdmi-frame-pack          HDMI frame packing mode
red-cyan-monochrome      Red/cyan glasses, monochrome
red-cyan-half-color      Red/cyan glasses, half color
red-cyan-full-color      Red/cyan glasses, full color
red-cyan-dubois          Red/cyan glasses, Dubois
green-magenta-monochrome Green/magenta glasses, monochrome
green-magenta-half-color Green/magenta glasses, half color
green-magenta-full-color Green/magenta glasses, full color
green-magenta-dubois     Green/magenta glasses, Dubois
amber-blue-monochrome    Amber/blue glasses, monochrome
amber-blue-half-color    Amber/blue glasses, half color
amber-blue-full-color    Amber/blue glasses, full color
amber-blue-dubois        Amber/blue glasses, Dubois
red-green-monochrome     Red/green glasses, monochrome
red-blue-monochrome      Red/blue glasses, monochrome
equalizer                Multi-display via Equalizer (2D setup)
equalizer-3d             Multi-display via Equalizer (3D setup)
```

---
blending video modes (--blendmode):
https://ffmpeg.org/ffmpeg-filters.html#blend_002c-tblend
---
```
‘addition’
‘grainmerge’
‘and’
‘average’
‘burn’
‘darken’
‘difference’
‘grainextract’
‘divide’
‘dodge’
‘freeze’
‘exclusion’
‘extremity’
‘glow’
‘hardlight’
‘hardmix’
‘heat’
‘lighten’
‘linearlight’
‘multiply’
‘multiply128’
‘negation’
‘normal’
‘or’
‘overlay’
‘phoenix’
‘pinlight’
‘reflect’
‘screen’
‘softlight’
‘subtract’
‘vividlight’
‘xor’
```

Setup on MacOS as an auto-login execution of tests:

use run_test.plist as a template, place in ~/Library/LaunchAgents/
then run "launchctl load -w ~/Library/LaunchAgents/run_test.plist"
to have it start on logon.
