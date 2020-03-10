from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.clean import cleanup
#import os

class DiamondNet( Topo ):
    """Define topology for mininet in lab 2"""

    def __init__( self ):
        Topo.__init__( self )
        # Add hosts and switches
        H1 = self.addHost( 'H1', ip='10.0.0.1/24' )
        H2 = self.addHost( 'H2', ip='10.0.0.2/24' )
        H3 = self.addHost( 'H3', ip='10.0.0.3/24' )
        H4 = self.addHost( 'H4', ip='10.0.0.4/24' )
        SA = self.addSwitch( 'S1' )
        SB = self.addSwitch( 'S2' )
        SC = self.addSwitch( 'S3' )
        SD = self.addSwitch( 'S4' )

        # Add links
        self.addLink( H1, SA )
        self.addLink( H2, SB )
        self.addLink( H3, SC )
        self.addLink( H4, SD )
        self.addLink( SA, SB )
        self.addLink( SB, SC )
        self.addLink( SC, SD )
        self.addLink( SD, SA )

'''
if __name__ == '__main__':
    setLogLevel('info')

    try:
        # Create and start mininet
        topo = DiamondNet()
        net = Mininet(topo)
        net.start()
        CLI(net)
        net.stop()

    except:
        cleanup()
'''
