Mac/Simple set bandwidth_ 55Mb

set MESSAGE_PORT 7
set MESSAGE_PORT_2 8
set BROADCAST_ADDR -1


#set val(chan)           Channel/WirelessChannel    ;#Channel Type
set val(prop)           Propagation/TwoRayGround   ;# radio-propagation model
set val(netif)          Phy/WirelessPhy            ;# network interface type



set val(mac)            Mac/802_11                 ;# MAC type
#set val(mac)            Mac                 ;# MAC type
#set val(mac)		Mac/Simple


set val(ifq)            Queue/DropTail/PriQueue    ;# interface queue type
set val(ll)             LL                         ;# link layer type
set val(ant)            Antenna/OmniAntenna        ;# antenna model
set val(ifqlen)         32768                         ;# max packet in ifq


set val(rp) DumbAgent

set ns [new Simulator]

set f [open rts-cts-data-ack_55Mbps.tr w]
$ns trace-all $f

set nf [open rts-cts-data-ack-temp.nam w]
$ns namtrace-all-wireless $nf 700 200

# set up topography object
set topo       [new Topography]

$topo load_flatgrid 700 200

#
# Create God
#
create-god 9

# create a loss_module and set its packet error rate to 1 percent
set loss_module [new ErrorModel]
$loss_module set rate_ 0.000001
# set target for dropped packets
$loss_module drop-target [new Agent/Null]

$ns node-config -adhocRouting $val(rp) \
                -llType $val(ll) \
                -macType $val(mac) \
                -ifqType $val(ifq) \
                -ifqLen $val(ifqlen) \
                -antType $val(ant) \
                -propType $val(prop) \
                -phyType $val(netif) \
		-channelType Channel/WirelessChannel \
                -topoInstance $topo \
                -agentTrace ON \
                -routerTrace OFF \
                -macTrace ON \
                -movementTrace OFF 

for {set i 0} {$i < 9} {incr i} {
	set node_($i) [$ns node]
	$node_($i) random-motion 0
}

$node_(0) color black
$node_(1) color black
$node_(2) color black


# A
$node_(0) set X_ 50.0
$node_(0) set Y_ 0.0
$node_(0) set Z_ 0.0

# B
$node_(1) set X_ 0.0
$node_(1) set Y_ 50.0
$node_(1) set Z_ 0.0

#D
$node_(3) set X_ 50.0
$node_(3) set Y_ 100.0
$node_(3) set Z_ 0.0

#C
$node_(2) set X_ 100.0
$node_(2) set Y_ 25.0
$node_(2) set Z_ 0.0

#E
$node_(4) set X_ 100.0
$node_(4) set Y_ 75.0
$node_(4) set Z_ 0.0

# G
$node_(5) set X_ 150.0
$node_(5) set Y_ 25.0
$node_(5) set Z_ 0.0

# F
$node_(6) set X_ 150.0
$node_(6) set Y_ 75.0
$node_(6) set Z_ 0.0

# H
$node_(7) set X_ 200.0
$node_(7) set Y_ 25.0
$node_(7) set Z_ 0.0

# L
$node_(8) set X_ 200.0
$node_(8) set Y_ 75.0
$node_(8) set Z_ 0.0

# subclass Agent/MessagePassing to make it do flooding

Class Agent/MessagePassing/Flooding -superclass Agent/MessagePassing

Agent/MessagePassing/Flooding instproc recv {source sport size data} {
    $self instvar messages_seen node_
    global ns 1 

    # extract message ID from message
    set message_id [lindex [split $data ":"] 0]

    puts "\nNode [$node_ node-addr] got message $message_id\n"
    if {([$node_ node-addr] == 8 && $source == 0)
        || ([$node_ node-addr] == 7 && $source == 3)} {
        $ns trace-annotate "[$node_ node-addr] received {$data} from $source"
        $ns trace-annotate "[$node_ node-addr] sending message $message_id"
    }
    if {[lsearch $messages_seen $message_id] == -1} {
	lappend messages_seen $message_id
        # if {([$node_ node-addr] == 8 && $source == 0)
        #     || ([$node_ node-addr] == 7 && $source == 3)} {
        #     $ns trace-annotate "[$node_ node-addr] received {$data} from $source"
        #     $ns trace-annotate "[$node_ node-addr] sending message $message_id"
        # }
        
	$self sendto $size $data 7 $sport
    $self sendto $size $data 8 $sport
    } 
    # else {
    #     if {([$node_ node-addr] == 8 && $source == 0)
    #         || ([$node_ node-addr] == 7 && $source == 3)} {
    #         $ns trace-annotate "[$node_ node-addr] received redundant message $message_id from $source"
    #     }
        
    # }
}

Agent/MessagePassing/Flooding instproc send_message {size message_id data port} {
    $self instvar messages_seen node_
    global ns MESSAGE_PORT 7
    global ns MESSAGE_PORT_2 8

    lappend messages_seen $message_id
    $ns trace-annotate "[$node_ node-addr] sending message $message_id"
    $self sendto $size "$message_id:$data" 7 $port
    $self sendto $size "$message_id:$data" 8 $port
}



# attach a new Agent/MessagePassing/Flooding to each node on port $MESSAGE_PORT
for {set i 0} {$i < 9} {incr i} {
    set a($i) [new Agent/MessagePassing/Flooding]
    $node_($i) attach  $a($i) $MESSAGE_PORT
    $node_($i) attach  $a($i) $MESSAGE_PORT_2
    $a($i) set messages_seen {}
}



for {set t 0} {$t < 100} {incr t} {
    $ns at $t*0.000001 "$a(0) send_message 500 1  {first_message} $MESSAGE_PORT"
    $ns at $t*0.000001 "$a(3) send_message 500 2  {second_message} $MESSAGE_PORT_2"
}



for {set i 0} {$i < 9} {incr i} {
	$ns initial_node_pos $node_($i) 30
	$ns at 1000.0 "$node_($i) reset";
}

$ns at 100.0 "finish"
$ns at 100.1 "puts \"NS EXITING...\"; $ns halt"



#INSERT ANNOTATIONS HERE

proc finish {} {
        global ns f nf val
        $ns flush-trace
        close $f
        close $nf

}

puts "Starting Simulation..."

$ns run