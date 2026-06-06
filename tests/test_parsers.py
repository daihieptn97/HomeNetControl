from app.services.network import parse_arp_scan, parse_nmap
from app.services.wifi import parse_iw_link, parse_iw_scan, parse_iwconfig, parse_nmcli_wifi


def test_parse_arp_scan():
    output = """
Interface: eth0, type: EN10MB, MAC: aa:bb:cc:dd:ee:ff, IPv4: 192.168.1.10
192.168.1.1     AA:BB:CC:00:00:01       Router Inc.
192.168.1.44    aa:bb:cc:00:00:44       Phone Vendor
"""
    devices = parse_arp_scan(output)
    assert len(devices) == 2
    assert devices[0].mac == "aa:bb:cc:00:00:01"
    assert devices[0].vendor == "Router Inc."


def test_parse_nmap():
    output = """
Nmap scan report for router.local (192.168.1.1)
Host is up (0.0040s latency).
MAC Address: AA:BB:CC:00:00:01 (Router Inc.)
Nmap scan report for 192.168.1.44
Host is up.
MAC Address: AA:BB:CC:00:00:44 (Phone Vendor)
"""
    devices = parse_nmap(output)
    assert len(devices) == 2
    assert devices[0].hostname == "router.local"
    assert devices[1].vendor == "Phone Vendor"


def test_parse_iw_link():
    output = """
Connected to 00:11:22:33:44:55 (on wlan0)
        SSID: HomeNet
        freq: 2437
        signal: -48 dBm
        tx bitrate: 72.2 MBit/s
"""
    data = parse_iw_link(output)
    assert data["ssid"] == "HomeNet"
    assert data["frequency_mhz"] == 2437
    assert data["band"] == "2.4 GHz"
    assert data["signal_dbm"] == -48


def test_parse_iwconfig():
    output = 'wlan0 IEEE 802.11 ESSID:"HomeNet" Frequency:5.18 GHz Bit Rate=433 Mb/s Signal level=-61 dBm'
    data = parse_iwconfig(output)
    assert data["ssid"] == "HomeNet"
    assert data["band"] == "5 GHz"
    assert data["signal_dbm"] == -61


def test_parse_iw_scan():
    output = """
BSS 00:11:22:33:44:55(on wlan0)
        freq: 2437
        capability: ESS Privacy ShortSlotTime (0x0411)
        signal: -48.00 dBm
        SSID: HomeNet
        RSN:     * Version: 1
BSS 00:11:22:33:44:66(on wlan0)
        freq: 5180
        signal: -58.00 dBm
        SSID: Guest
"""
    networks = parse_iw_scan(output)
    assert networks[0]["ssid"] == "HomeNet"
    assert networks[0]["security"] == "WPA2/RSN"
    assert networks[0]["channel"] == "6"
    assert networks[1]["band"] == "5 GHz"


def test_parse_nmcli_wifi():
    output = "HomeNet:87:2437:WPA2\\ WPA3\nCafe\\:Wifi:42:2462:WPA2\n"
    networks = parse_nmcli_wifi(output)
    assert networks[0]["ssid"] == "HomeNet"
    assert networks[0]["signal_percent"] == 87
    assert networks[1]["ssid"] == "Cafe:Wifi"
