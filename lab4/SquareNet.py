from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.clean import cleanup
from functools import partial

RYU_IP = '192.168.56.1'

class SquareNet( Topo ):
    """Define topology in Lab 4"""

    def __init__( self ):
        Topo.__init__( self )
        # Add hosts and switches
        H1 = self.addHost( 'H1', ip='10.0.1.1/24' )
        H2 = self.addHost( 'H2', ip='10.0.2.1/24' )
        H3 = self.addHost( 'H3', ip='10.0.3.1/24' )
        H4 = self.addHost( 'H4', ip='10.0.4.1/24' )
        S1 = self.addSwitch( 'S1' )
        S2 = self.addSwitch( 'S2' )
        S3 = self.addSwitch( 'S3' )
        S4 = self.addSwitch( 'S4' )

        # Add links
        self.addLink( H1, S1 )
        self.addLink( H2, S2 )
        self.addLink( H3, S3 )
        self.addLink( H4, S4 )
        self.addLink( S1, S2 )
        self.addLink( S2, S3 )
        self.addLink( S3, S4 )
        self.addLink( S4, S1 )

topos = {'squarenet': SquareNet}

if __name__ == '__main__':
    setLogLevel('info')

    try:
        # Create and start mininet
        net = Mininet(topo=SquareNet(), \
		              switch=partial(OVSSwitch, protocols='OpenFlow13'), \
		              controller=RemoteController('ryu', RYU_IP)) 
        net.start()
        CLI(net)
        net.stop()

    except:
        cleanup()

