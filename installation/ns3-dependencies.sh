#!/usr/bin/env bash

# Works for ubunu 18.04

# install all needed pre-requisites for ns3 before release 3.36 (waf build system)
sudo apt-get -y --no-install-recommends install gcc g++ python python-dev
sudo apt-get -y --no-install-recommends install qt5-default mercurial

#only before ubuntu 18.04
sudo apt-get -y --no-install-recommends install python-pygraphviz python-kiwi python-pygoocanvas libgoocanvas-dev ipython
sudo apt-get -y --no-install-recommends install gir1.2-goocanvas-2.0 python-gi python-gi-cairo python-pygraphviz python3-gi python3-gi-cairo python3-pygraphviz gir1.2-gtk-3.0 ipython ipython3

# mpi based distributed emulation support
sudo apt-get -y --no-install-recommends install openmpi-bin openmpi-common openmpi-doc libopenmpi-dev

# support for bake
sudo apt-get -y --no-install-recommends install autoconf cvs bzr unrar

# debugging support
sudo apt-get -y --no-install-recommends install gdb valgrind

# support for utils/check-style.py
sudo apt-get -y --no-install-recommends install uncrustify

# support for doxygen and documentation
sudo apt-get -y --no-install-recommends install doxygen graphviz imagemagick
sudo apt-get -y --no-install-recommends install texlive texlive-extra-utils texlive-latex-extra texlive-font-utils texlive-lang-portuguese dvipng latexmk
sudo apt-get -y --no-install-recommends install python-sphinx dia

# pcap
sudo apt-get -y --no-install-recommends install tcpdump

# statistics framework
sudo apt-get -y --no-install-recommends install sqlite sqlite3 libsqlite3-dev
sudo apt-get -y --no-install-recommends install libxml2 libxml2-dev

# python bindings
sudo apt-get -y --no-install-recommends install cmake libc6-dev libc6-dev-i386 libclang-dev llvm-dev automake
sudo pip install cxxfilt

# gcc 9 for the servers
# https://gist.github.com/jlblancoc/99521194aba975286c80f93e47966dc5 (doc)
sudo apt-get -y --no-install-recommends install -y software-properties-common
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt update
sudo apt install g++-9 -y

sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 \
                         --slave /usr/bin/g++ g++ /usr/bin/g++-9
sudo update-alternatives --config gcc
gcc --version
g++ --version

# Add all the g++ and other libs stuff

DEPENDENCIES_DIR="/home/fancy/fancy/dependencies/"

mkdir -p ${DEPENDENCIES_DIR}

cd $DEPENDENCIES_DIR
git clone https://github.com/nlohmann/json.git
cd json
mkdir build
cd build 
cmake ..
sudo make install

# install filesystem c++
# boost 1.72
# https://www.boost.org/doc/libs/1_72_0/more/getting_started/unix-variants.html
# http://www.linuxfromscratch.org/blfs/view/svn/general/boost.html
# new link https://boostorg.jfrog.io/artifactory/main/release/1.72.0/source/boost_1_72_0.tar.gz

# if the system boost is installed then it does not recognize it
# to remove
# sudo apt-get purge libboost* 
cd $DEPENDENCIES_DIR
wget https://boostorg.jfrog.io/artifactory/main/release/1.72.0/source/boost_1_72_0.tar.gz
tar -xvf boost_1_72_0.tar.gz
cd boost_1_72_0
sudo ./bootstrap.sh --prefix=/usr/local --with-libraries=all
sudo ./b2 install
sudo /bin/bash -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/boost.conf'
sudo ldconfig


