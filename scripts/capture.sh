#!/bin/bash
#
# web-ui http://fritz.box/html/capture.html
#
HOST="fritz.box"
ARGUMENTS=""
IFACE=""

function get_session_id() {
    local SID
    CHALLENGE=$(wget -O - "http://$HOST/login_sid.lua" 2>/dev/null \
        | sed 's/.*<Challenge>\(.*\)<\/Challenge>.*/\1/')

    CPSTR="$CHALLENGE-$PASSWORD"
    MD5=$(echo -n $CPSTR | iconv -f ISO8859-1 -t UTF-16LE \
        | md5sum -b | awk '{print substr($0,1,32)}')
    RESPONSE="$CHALLENGE-$MD5"

    SID=$(wget -O - --post-data="?username=&response=$RESPONSE" \
        "http://$HOST/login_sid.lua" 2>/dev/null \
        | sed 's/.*<SID>\(.*\)<\/SID>.*/\1/')
    echo "$SID"
}

echo -n "Enter your router password: "; read PASSWORD;
SID=$(get_session_id)
if [ "$SID" == "0000000000000000" ]; then
    echo "Authentication failure!"
    exit
fi

echo ""
echo "What do you want to capture?"
echo "INTERNET:"
echo "   1) Internet"
echo "   2) Interface 0"
echo "   3) Routing Interface"
echo "INTERFACES:"
echo "   4) tunl0"
echo "   5) eth0"
echo "   6) eth1"
echo "   7) eth2"
echo "   8) eth3"
echo "   9) lan"
echo "  10) hotspot"
echo "  11) wifi0"
echo "  12) ath0"
echo "WIFI:"
echo "  13) AP 2,4 GHz ath0, Interface 1"
echo "  14) AP 2,4 GHz ath0, Interface 0"
echo "  15) HW 2,4 GHz wifi0, Interface 0"
echo ""

while true; do 
    echo -n "Enter your choice [0-15] ('q' for quit): "; read MODE;
    if (("$MODE" > "0")) && (("$MODE" < "16")); then
        if [ "$MODE" == "1" ]; then
            IFACE="2-1"
        elif [ "$MODE" == "2" ]; then
            IFACE="3-17"
        elif [ "$MODE" == "3" ]; then
            IFACE="3-0"
        elif [ "$MODE" == "4" ]; then
            IFACE="1-tunl0"
        elif [ "$MODE" == "5" ]; then
            IFACE="1-eth0"
        elif [ "$MODE" == "6" ]; then
            IFACE="1-eth1"
        elif [ "$MODE" == "7" ]; then
            IFACE="1-eth2"
        elif [ "$MODE" == "8" ]; then
            IFACE="1-eth3"
        elif [ "$MODE" == "9" ]; then
            IFACE="1-lan"
        elif [ "$MODE" == "10" ]; then
            IFACE="1-hotspot"
        elif [ "$MODE" == "11" ]; then
            IFACE="1-wifi0"
        elif [ "$MODE" == "12" ]; then
            IFACE="1-ath0"
        elif [ "$MODE" == "13" ]; then
            IFACE="4-131"
        elif [ "$MODE" == "14" ]; then
            IFACE="4-130"
        elif [ "$MODE" == "15" ]; then
            IFACE="4-128"
        fi
        break
    elif [ "$MODE" == "q" ]; then
        exit
    fi
done

echo ""
echo "Do you also want to write a pcap file?"
echo ""

while true; do 
    echo -n "Enter your choice [y-n] ('q' for quit): "; read WRITE_PCAP;
    if [ "$WRITE_PCAP" == "y" ]; then
        PCAP_FILE="$(date +%Y-%m-%d_%H:%M:%S).pcap"
        WIRESHARK_ARGS="-w $PCAP_FILE"
        break
    elif [ "$WRITE_PCAP" == "n" ]; then
        WIRESHARK_ARGS=""
        break
    elif [ "$WRITE_PCAP" == "q" ]; then
        exit
    fi
done

echo ""
echo "Starting wireshark ..."
echo ""

wget -O - "http://$HOST/cgi-bin/capture_notimeout?ifaceorminor=$IFACE&snaplen=1600&capture=Start&sid=$SID" \
    2>/dev/null \
    | wireshark -k $WIRESHARK_ARGS -i -
