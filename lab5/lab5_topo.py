"""
Topooly for EL9333 Lab 5

"""

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.clean import cleanup
from functools import partial
import os

RYU_IP = '192.168.56.1'

class MyTopo( Topo ):

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        # Hosts
        leftHost            = self.addHost( 'h1' )
        rightHost           = self.addHost( 'h2' )
        # Switches
        leftCoreSwitch      = self.addSwitch( 's1' )
        middleCoreSwitch    = self.addSwitch( 's2' )
        rightCoreSwitch     = self.addSwitch( 's3' )
        leftEdgeSwitch      = self.addSwitch( 's4' )
        righEdgetSwitch     = self.addSwitch( 's5' )

        # Add links
        self.addLink( leftHost        , leftEdgeSwitch   , 1 , 1 )
        self.addLink( rightHost       , righEdgetSwitch  , 1 , 1 )

        self.addLink( leftEdgeSwitch  , leftCoreSwitch   , 2 , 1 )
        self.addLink( leftEdgeSwitch  , middleCoreSwitch , 3 , 1 )
        self.addLink( leftEdgeSwitch  , rightCoreSwitch  , 4 , 1 )

        self.addLink( righEdgetSwitch , leftCoreSwitch   , 2 , 2 )
        self.addLink( righEdgetSwitch , middleCoreSwitch , 3 , 2 )
        self.addLink( righEdgetSwitch , rightCoreSwitch  , 4 , 2 )


topos = { 'mytopo': ( lambda: MyTopo() ) }

if __name__ == '__main__':
    setLogLevel('info')

    try:
        # Create and start mininet
        net = Mininet(topo=MyTopo(), autoSetMacs=True, autoStaticArp=True, \
                      switch=partial(OVSSwitch, protocols='OpenFlow13'), \
		              controller=RemoteController('ryu', RYU_IP)) 
        # net = Mininet(topo=MyTopo(), switch=partial(OVSSwitch, protocols='OpenFlow13'))
        net.start()

        os.system('ovs-vsctl --id=@core create flow_table flow_limit=100 overflow_policy=refuse \
                             -- set bridge s1 flow_tables:0=@core \
                             -- set bridge s2 flow_tables:0=@core \
                             -- set bridge s3 flow_tables:0=@core')   
        CLI(net) 
        net.stop()

    except:
        cleanup()