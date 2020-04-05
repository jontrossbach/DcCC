from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import packet, ethernet, arp, ipv4, tcp

class RemoteRYU(app_manager.RyuApp):
    """Define a remote controller in Lab 4"""

    # specify OF1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self):
        super(RemoteRYU, self).__init__()
        # register host ip & mac table.
        self.host_ip = dict([('10.0.0.%s'%(id+1), id+1) for id in range(4)])
        self.host_mac = dict([(id+1, ('00:00:00:00:00:0%s'%(id+1))) for id in range(4)])

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0, match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        in_port = msg.match['in_port']
    
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # analyse protocols 
        pkt = packet.Packet(msg.data)

        if pkt.get_protocol(arp.arp):
            # handle arp requests from hosts, but it's unnecessary if autosSetArp is enabled in mininet
            pkt_eth = pkt.get_protocol(ethernet.ethernet)
            pkt_arp = pkt.get_protocol(arp.arp)           
            self.logger.info("packet in (S%s): arp_request src %s dst %s in_port %s", dpid, pkt_arp.src_ip, pkt_arp.dst_ip, in_port)
            self._arp_handler(in_port, datapath, dpid, ofproto, parser, pkt_eth, pkt_arp)
        elif pkt.get_protocol(ipv4.ipv4):
            # install different rules as specified
            pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
            ip_proto = pkt_ipv4.proto
            ip_src = pkt_ipv4.src
            ip_dst = pkt_ipv4.dst
            # confirm which two hosts are communicating
            host_src = self.host_ip[ip_src]
            host_dst = self.host_ip[ip_dst]
        
            pkt_tcp = pkt.get_protocol(tcp.tcp)
            sqn = pkt_tcp.seq
            offset = pkt_tcp.offset
            if pkt_tcp and (pkt_tcp.dst_port == 80) and (dpid == 1 or dpid == 3) and (host_src == 2 or host_src == 4) and (host_dst == 2 or host_dst == 4):              
                pkt_eth = pkt.get_protocol(ethernet.ethernet)
                self._http_handler(msg, in_port, datapath, dpid, ofproto, parser, ip_proto, ip_src, ip_dst, pkt_eth, pkt_ipv4, sqn, offset)
            else:
                self._ipv4_handler(msg, in_port, datapath, dpid, ofproto, parser, ip_proto, ip_src, ip_dst, host_src, host_dst, sqn, offset)

    def _arp_handler(self, in_port, datapath, dpid, ofproto, parser, pkt_eth, pkt_arp):
        # confirm the target of arp request, and send an arp reply to answer call
        target_id = self.host_ip[pkt_arp.dst_ip]
        target_mac = self.host_mac[target_id]

        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_eth.ethertype, dst=pkt_eth.src, src=target_mac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=target_mac, src_ip=pkt_arp.dst_ip, dst_mac=pkt_arp.src_mac, dst_ip=pkt_arp.src_ip))
        pkt.serialize()

        actions = [parser.OFPActionOutput(in_port, ofproto.OFPCML_NO_BUFFER)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        self.logger.info("packet out (S%s): arp_reply src %s dst %s out_port %s\n", dpid, pkt_arp.dst_ip, pkt_arp.src_ip, in_port)
        datapath.send_msg(out)

    def _http_handler(self, msg, in_port, datapath, dpid, ofproto, parser, ip_proto, ip_src, ip_dst, pkt_eth, pkt_ipv4, sqn, offset):
        print('dpid ', dpid)
        self.logger.info("packet in (S%s): http src %s dst %s in_port %s sqn %s offset %s", dpid, ip_src, ip_dst, in_port, sqn, offset)
        match = parser.OFPMatch(in_port=in_port, eth_type=ethernet.ether.ETH_TYPE_IP, ipv4_dst=ip_dst, ipv4_src=ip_src, ip_proto=ip_proto, tcp_dst=80)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=2, match=match, instructions=inst)
        self.logger.info("add flow (S%s): http src %s dst %s out_port controller", dpid, ip_src, ip_dst)
        datapath.send_msg(mod)
        
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_eth.ethertype, dst=self.host_mac[dpid], src=pkt_eth.src))
        pkt.add_protocol(ipv4.ipv4(proto=ip_proto, src=ip_src, dst=list(self.host_ip.keys())[dpid-1]))
        pkt.add_protocol(tcp.tcp(bits=tcp.TCP_RST, ack=sqn))
        pkt.serialize()

        actions = [parser.OFPActionOutput(1, ofproto.OFPCML_NO_BUFFER)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        self.logger.info("packet out (S%s): http rst src %s dst %s out_port 1\n", dpid, ip_src, list(self.host_ip.keys())[dpid-1])
        datapath.send_msg(out)

    def _ipv4_handler(self, msg, in_port, datapath, dpid, ofproto, parser, ip_proto, ip_src, ip_dst, host_src, host_dst, sqn, offset):
        if ip_proto == 1:
            ipv4_type = 'icmp'
        elif ip_proto == 6:
            ipv4_type = 'tcp'
        elif ip_proto == 17:
            ipv4_type = 'udp'
        else:
            return
        self.logger.info("packet in (S%s): %s src %s dst %s in_port %s sqn %s offset %s", dpid, ipv4_type, ip_src, ip_dst, in_port, sqn, offset)

        # handle h1 and h4 udp case in particular
        if ipv4_type == 'udp' and (host_src == 1 or host_src == 4) and (host_dst == 1 or host_dst == 4):
            match = parser.OFPMatch(in_port=in_port, eth_type=ethernet.ether.ETH_TYPE_IP, ipv4_dst=ip_dst, ipv4_src=ip_src, ip_proto=ip_proto)
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, [])]
            mod = parser.OFPFlowMod(datapath=datapath, priority=2, match=match, instructions=inst)
            self.logger.info("add flow (S%s): udp src %s dst %s drop\n", dpid, ip_src, ip_dst)
            datapath.send_msg(mod)
            return

        # route rules; setting particular order of linking interfaces in mininet is convenient for algorithm implementation
        if host_dst == dpid:
            out_port = 1
        else:
            host_diff = abs(host_src - host_dst)
            if host_diff == 1:    # shortest path
                out_port = (2,3)[host_src>host_dst]
            elif host_diff == 2:  # specified clock-wise path
                out_port = 3 if ipv4_type == 'udp' else 2    
            elif host_diff == 3:  # shortest path
                out_port = (2,3)[host_src<host_dst]

        match = parser.OFPMatch(in_port=in_port, eth_type=ethernet.ether.ETH_TYPE_IP, ipv4_dst=ip_dst, ip_proto=ip_proto)
        actions = [parser.OFPActionOutput(out_port, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst)
        self.logger.info("add flow (S%s): %s src %s dst %s out_port %s", dpid, ipv4_type, ip_src, ip_dst, out_port)
        datapath.send_msg(mod)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=msg.data)
        self.logger.info("packet out (S%s): %s src %s dst %s out_port %s\n", dpid, ipv4_type, ip_src, ip_dst, out_port)
        datapath.send_msg(out)
