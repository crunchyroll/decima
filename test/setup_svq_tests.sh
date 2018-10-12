#!/bin/sh

basedir="$1"
testset="$2"

#set -e
#set -v

unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac
echo "Building for $machine system"

msudir=$(pwd)
bindir=$msudir

# setup bin dir for scripts/binaries
export PATH=$bindir:$PATH

# conifirm ffmpeg is installed
ffmpegcheck=$(which ffmpeg)
if [ "$ffmpegcheck" = "" ]; then
    echo "Error: Missing ffmpeg, please install"
    if [ "$machine" = "Mac" ]; then
        echo " mac: brew install ffmpeg --with-theora --with-srt --with-libvpx --with-openssl --with-fdk-aac --with-fontconfig --with-freetype --with-fontconfig --with-libass"
    fi
    if [ "$machine" = "Linux" ]; then
        echo " linux: sudo yum install ffmpeg"
    fi
    exit 1
fi

# conifirm mediainfo is installed
mediainfocheck=$(which mediainfo)
if [ "$mediainfocheck" = "" ]; then
    echo "Error: Missing mediainfo, please install"
    if [ "$machine" = "Mac" ]; then
        echo " mac: brew install mediainfo"
    fi
    if [ "$machine" = "Linux" ]; then
        echo " linux: sudo yum install mediainfo"
    fi
    exit 1
fi

# conifirm gnuplot is installed
gnuplotcheck=$(which gnuplot)
if [ "$gnuplotcheck" = "" ]; then
    echo "Error: Missing gnuplot, please install"
    if [ "$machine" = "Mac" ]; then
        echo " mac: brew install gnuplot"
    fi
    if [ "$machine" = "Linux" ]; then
        echo " linux: sudo yum install gnuplot"
    fi
    exit 1
fi

# conifirm mpv is installed
mpvcheck=$(which mpv)
if [ "$mpvcheck" = "" ]; then
    echo "Error: Missing mpv, please install"
    if [ "$machine" = "Mac" ]; then
        echo " mac: brew install mpv"
    fi
    if [ "$machine" = "Linux" ]; then
        echo " linux: https://github.com/mpv-player/mpv/releases/"
    fi
    exit 1
fi

# check for Bino
if [ ! -d /Applications/Bino.app ]; then
    echo "Warning: Missing Bino, optionally install"
    if [ "$machine" = "Mac" ]; then
        echo " mac: "
        echo "   wget http://devernay.free.fr/hacks/bino/Bino-1.6.6-OSX-Mavericks-GPL.zip"
        echo "   unzip Bino-1.6.6-OSX-Mavericks-GPL.zip"
        echo "   sudo rsync -av Bino.app/ /Applications/Bino.app/"
    fi
    if [ "$machine" = "Linux" ]; then
        echo " linux: https://bino3d.org/download.html"
    fi
fi

# cut mezz from cloudfront location to local clips
# then encode them and analyze for test creation
all_tasks=$(echo $(for f in $(ls ${basedir}tasks/${testset}/*/task.json | sort); do printf "$f,"; done) | sed -e s/,\$//g)
cmd="create_task.py --tasks_file $all_tasks"
$cmd

echo "Finished setting up tests!"
echo ""
echo "To execute tests run:"
echo " ./test/run_svq_tests.sh $basedir $testset"


