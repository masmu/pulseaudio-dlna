#!/bin/bash

function lecho() {
    echo ""
    echo "####################################################################"
    echo "# $1"
    echo "####################################################################"
}

function install_tmate() {
    ensure_private_ssh_key
    lecho 'Installing tmate ...'
    hash tmate 2>/dev/null || {
        sudo add-apt-repository -y ppa:tmate.io/archive
        sudo apt-get update
        sudo apt-get -y install tmate tmux
    }
    hash tmux 2>/dev/null || {
        sudo apt-get -y install tmux
    }
    [[ -f ~/.tmate.conf ]] || {
        echo 'set -g terminal-overrides ""' > ~/.tmate.conf
        echo 'set -g xterm-keys on' >> ~/.tmate.conf
        echo 'source-file /usr/share/doc/tmux/examples/screen-keys.conf' >> ~/.tmate.conf
    }
    echo 'ok!'
}

function remove_tmate() {
    lecho 'Removing tmate ...'
    sudo apt-get remove tmate
    sudo ppa-purge ppa:tmate.io/archive
}

function run_tmate() {
    hash tmate 2>/dev/null && tmate
}

function ensure_private_ssh_key() {
    lecho 'Ensuring you have a private ssh key ...'
    if [ ! -f ~/.ssh/id_rsa ]; then
        ssh-keygen -f ~/.ssh/id_rsa -t rsa -b 4096 -N ""
    fi
    echo 'ok!'
}

function install_fonts() {
    lecho 'Installing powerline fonts'
    if [ ! -d /tmp/fonts ]; then
        git clone https://github.com/powerline/fonts.git /tmp/fonts
        bash /tmp/fonts/install.sh
        hash gsettings 2>/dev/null && {
            gsettings set org.gnome.desktop.interface monospace-font-name \
                "Droid Sans Mono Dotted for Powerline 9";
        }
    fi
    echo 'ok!'
}

function install_dev() {
    sudo apt-get install \
        python3 \
        python3-pip \
        python3-setuptools \
        python3-dbus \
        python3-docopt \
        python3-requests \
        python3-setproctitle \
        python3-gi \
        python3-notify2 \
        python3-psutil \
        python3-chardet \
        python3-netifaces \
        python3-netaddr \
        python3-pyroute2 \
        python3-lxml \
        python3-pychromecast \
        vorbis-tools \
        sox \
        lame \
        flac \
        opus-tools \
        pavucontrol \
        virtualenv python3-dev git-core
    [[ -d ~/pulseaudio-dlna ]] || \
        git clone https://github.com/masmu/pulseaudio-dlna.git ~/pulseaudio-dlna
}

while [ "$#" -gt "0" ]; do
    case $1 in
    --remote | --tmate)
        install_tmate
        run_tmate
        exit 0
    ;;
    --install-tmate)
        install_tmate
        exit 0
    ;;
    --install-fonts)
        install_fonts
        exit 0
    ;;
    --remove-tmate)
        remove_tmate
        exit 0
    ;;
    --dev)
        install_dev
        exit 0
    ;;
    *)
        echo "Unknown option '$1'!"
        exit 1
    ;;
    esac
done

echo "You did not specify any arguments!"
exit 1