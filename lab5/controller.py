from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import packet, ethernet, tcp

MPATH = True

class RemoteRYU(app_manager.RyuApp):
    """Define a remote controller in Lab 5"""

    # specify OF1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self):
        super(RemoteRYU, self).__init__()

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

        if pkt.get_protocol(tcp.tcp):
            pkt_tcp = pkt.get_protocol(tcp.tcp)
            self.logger.info("packet in (S%s): TCP in_port %s src_port %s dst_port %s", dpid, in_port, pkt_tcp.src_port, pkt_tcp.dst_port)
            if MPATH:
                if dpid == 4 or dpid == 5:
                    out_port = 1 if in_port != 1 else pkt_tcp.dst_port%3+2
                else:
                    out_port = 2 if in_port == 1 else 1
            else:
                out_port = 2 if in_port == 1 else 1

            match = parser.OFPMatch(in_port=in_port, eth_type=ethernet.ether.ETH_TYPE_IP, ip_proto=6, tcp_dst=pkt_tcp.dst_port)
            actions = [parser.OFPActionOutput(out_port, ofproto.OFPCML_NO_BUFFER)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst)
            self.logger.info("add flow (S%s): TCP in_port %s src_port %s dst_port %s out_port %s", dpid, in_port, pkt_tcp.src_port, pkt_tcp.dst_port, out_port)
            datapath.send_msg(mod)

            out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=msg.data)
            self.logger.info("packet out (S%s): TCP dst_port %s out_port %s\n", dpid, pkt_tcp.dst_port, out_port)
            datapath.send_msg(out)

