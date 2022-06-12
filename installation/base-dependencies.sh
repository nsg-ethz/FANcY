# Science Plot Library requires latex to be installed 
# https://github.com/garrettj403/SciencePlots

# latex
sudo apt-get -y --no-install-recommends install dvipng texlive-latex-extra texlive-fonts-recommended cm-super

# pip3
sudo apt-get -y --no-install-recommends install python3-pip
sudo pip3 install --upgrade pip
sudo pip3 install --upgrade setuptools
# required before the rest
sudo pip3 install matplotlib