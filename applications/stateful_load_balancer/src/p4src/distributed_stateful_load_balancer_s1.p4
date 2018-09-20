#include "distributed_stateful_load_balancer_sync_header.p4"
#include "distributed_stateful_load_balancer_s1_sync.p4"
// ------------------ Constants --------------------


// -------------------- Headers ------------------------

header_type load_balancer_t {
    fields {
        preamble: 64;
        syn: 32;
        fin: 32;
        fid: 32;
        subfid : 32;
        packet_id : 32;
        hash : 32;
        _count : 32;
    }
}

header load_balancer_t load_balancer_head;

header_type meta_t {
    fields {
        temp : 32;

            server_flow1 : 32;
            server_flow2 : 32;

            switch_flow1 : 32;
            switch_flow2 : 32;
            switch_flow3 : 32;
            switch_flow4 : 32;

        hash: 16;
        routing_port: 32;

        probe_bool : 32;

        upper_limit : 32;
        lower_limit : 32;
    }
}
metadata meta_t meta;

// ---------------------- Hashing ------------------

field_list flow_list {
    load_balancer_head.fid;
}

field_list_calculation flow_register_index {
    input {
        flow_list;
    }
    algorithm : crc16;
    output_width : 16;
}

//-------------------- Parsers ------------------------

parser start {
    return select(current(0, 64)) {
        0: parse_head;
        1: parse_head;
        2: parse_head_and_sync;
        default: ingress;
    }
}

parser parse_head {
    extract(load_balancer_head);
    return ingress;
}

parser parse_head_and_sync {
    extract(load_balancer_head);
    extract(sync_info);
    return ingress;
}

//------------------ Registers -----------------------

register total_flow_count_register {
    width: 32;
    instance_count: 7;
}

register flow_to_port_map_register {
    width: 32;
    instance_count: 65536;
}

// --------------------- Tables -------------------------------

table get_limits_table{
    actions{
        get_limits;
    }
    size:1;
}

table get_server_flow_count_table{
    actions{
        get_server_flow_count;
    }
    size:1;
}

table update_switch_flow_count_table {
    actions{
        update_switch_flow_count;
    }
    size: 1;
}

table set_server_dest_port_table{
    reads{
            meta.server_flow1 : exact;
            meta.server_flow2 : exact;
    }
    actions{
        set_server_dest_port;
    }
    size:25;
}

table set_probe_bool_table {
    actions{
        set_probe_bool;
    }
    size: 1;
}

table get_switch_flow_count_table{
    actions{
        get_switch_flow_count;
    }
    size:1;
}

    table set_switch1_dest_port_table{
        actions{
            set_switch1_dest_port;
        }
        size:1;
    }
    table set_switch2_dest_port_table{
        actions{
            set_switch2_dest_port;
        }
        size:1;
    }
    table set_switch3_dest_port_table{
        actions{
            set_switch3_dest_port;
        }
        size:1;
    }
    table set_switch4_dest_port_table{
        actions{
            set_switch4_dest_port;
        }
        size:1;
    }

table update_map_table {
    actions {
        update_map;
    }
    size: 1;
}

table forwarding_table {
    reads{
        meta.routing_port: valid;
    }
    actions{
        forward;
        _drop;
    }
    size: 1;
}

table drop_table {
    actions {
        _drop;
    }
    size: 1;
}

table clear_map_table {
    actions {
        clear_map;
    }
    size: 1;
}

table update_flow_count_table {
    actions{
        update_flow_count;
    }
    size: 1;
}

// ---------------------------- Actions -----------------------

action get_limits(upper_limit, lower_limit){
    modify_field(meta.upper_limit, upper_limit);
    modify_field(meta.lower_limit, lower_limit);
}

action get_server_flow_count(){

        register_read(meta.server_flow1, total_flow_count_register, 1 - 1);
        register_read(meta.server_flow2, total_flow_count_register, 2 - 1);
}

action update_switch_flow_count() {
    register_write(total_flow_count_register, standard_metadata.ingress_port - 2, sync_info._0);
}

action set_server_dest_port(flow_count,flow_dest){
    register_write(total_flow_count_register, flow_dest - 2, flow_count + 1);
    modify_field(standard_metadata.egress_spec, flow_dest);
}

action set_probe_bool(){
    modify_field(meta.probe_bool, 1);
}

action get_switch_flow_count(){
        register_read(meta.switch_flow1, total_flow_count_register, 1 + 3 - 2);
        register_read(meta.switch_flow2, total_flow_count_register, 2 + 3 - 2);
        register_read(meta.switch_flow3, total_flow_count_register, 3 + 3 - 2);
        register_read(meta.switch_flow4, total_flow_count_register, 4 + 3 - 2);
}

    action set_switch1_dest_port(){
        register_write(total_flow_count_register, 1 + 3 - 2, meta.switch_flow1 + 1);
        modify_field(standard_metadata.egress_spec, 1 + 3);
    }
    action set_switch2_dest_port(){
        register_write(total_flow_count_register, 2 + 3 - 2, meta.switch_flow2 + 1);
        modify_field(standard_metadata.egress_spec, 2 + 3);
    }
    action set_switch3_dest_port(){
        register_write(total_flow_count_register, 3 + 3 - 2, meta.switch_flow3 + 1);
        modify_field(standard_metadata.egress_spec, 3 + 3);
    }
    action set_switch4_dest_port(){
        register_write(total_flow_count_register, 4 + 3 - 2, meta.switch_flow4 + 1);
        modify_field(standard_metadata.egress_spec, 4 + 3);
    }

action update_map() {
    modify_field_with_hash_based_offset(meta.hash, 0, flow_register_index, 65536);
    register_write(flow_to_port_map_register, meta.hash, standard_metadata.egress_spec);
}

action forward() {
    modify_field_with_hash_based_offset(meta.hash, 0, flow_register_index, 65536);
    register_read(meta.routing_port, flow_to_port_map_register, meta.hash);
    modify_field(standard_metadata.egress_spec, meta.routing_port);
}

action clear_map() {
    modify_field_with_hash_based_offset(meta.hash, 0, flow_register_index, 65536);
    register_write(flow_to_port_map_register, meta.hash, 0);
}

action update_flow_count() {
    register_read(meta.temp, total_flow_count_register, meta.routing_port-2);
    add_to_field(meta.temp, -1);
    register_write(total_flow_count_register, meta.routing_port-2, meta.temp);
}

action _drop() {
    drop();
}

//------------------------ Control Logic -----------------

control ingress {

    //Get threshold from table instead of hardcoding
    apply(get_limits_table);  

    //Get server flow counts from the table  
    apply(get_server_flow_count_table); 

    //Preamble 1 => Probe packet 
    if (load_balancer_head.preamble == 1){

        //Send update (set preamble as 2)
        apply(echo_info1_table);
    }

    //Preamble 2 => Update packet
    else if (load_balancer_head.preamble == 2){
        //update the registers
        apply(update_switch_flow_count_table);
    }

    //Default Preamble is 0
    else {

        //-------------------------------------------------------------------------
        //Start of flow
        if(load_balancer_head.syn == 1) {

            //forwarding to own server
if(meta.server_flow1 < 4 or meta.server_flow2 < 4){
                
                //forwarding can be done locally
                apply(set_server_dest_port_table);

                //Take decision to send probe packet or not (Reactive)
if ((meta.server_flow1 + meta.server_flow2)*100 > (meta.upper_limit * 2 * 4)){
                    apply(set_probe_bool_table);
                }
            }
            
            //forwarding to another switch
            else{
                //Choose from switches
                apply(get_switch_flow_count_table);

                //all switches reach threshold
if (meta.switch_flow1 >= 2*4 and meta.switch_flow2 >= 2*4 and meta.switch_flow3 >= 2*4 and meta.switch_flow4 >= 2*4){
                    apply(drop_table);
                }

                //choose the switch handling least number of flows
                else {
                        if(meta.switch_flow1 <= meta.switch_flow2 and meta.switch_flow1 <= meta.switch_flow3 and meta.switch_flow1 <= meta.switch_flow4) {
                            apply(set_switch1_dest_port_table);
                        }
                        else if(meta.switch_flow2 <= meta.switch_flow1 and meta.switch_flow2 <= meta.switch_flow3 and meta.switch_flow2 <= meta.switch_flow4) {
                            apply(set_switch2_dest_port_table);
                        }
                        else if(meta.switch_flow3 <= meta.switch_flow1 and meta.switch_flow3 <= meta.switch_flow2 and meta.switch_flow3 <= meta.switch_flow4) {
                            apply(set_switch3_dest_port_table);
                        }
                        else if(meta.switch_flow4 <= meta.switch_flow1 and meta.switch_flow4 <= meta.switch_flow2 and meta.switch_flow4 <= meta.switch_flow3) {
                            apply(set_switch4_dest_port_table);
                        }
                }
                
            }

            //Remember mapping for the flow
            apply(update_map_table);
        }
        //-------------------------------------------------------------------------

        //forwarding
        apply(forwarding_table);

        if(meta.probe_bool == 1){
            apply(sync_info1_table);
        }

        //-------------------------------------------------------------------------
        //End of flow
        if(load_balancer_head.fin == 1) {

            //Clear mappings
            apply(clear_map_table);
            apply(update_flow_count_table);

            //Take decision to send probe packet or not (Proactive)
if ((meta.server_flow1 + meta.server_flow2)*100 < (meta.lower_limit * 2 * 4)){
                if(meta.routing_port == 2 or meta.routing_port == 3){

                    //Send broadcast (set preamble as 2)
                    apply(sync_info2_table);
                }
            }
        }
        //-------------------------------------------------------------------------
    }
}

control egress {
}
