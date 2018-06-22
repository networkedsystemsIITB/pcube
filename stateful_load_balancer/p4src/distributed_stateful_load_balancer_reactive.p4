/* Copyright 2018-present IIT Bombay (Akash Trehan, Huzefa Chasmai, Aniket Shirke)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// ------------------ Constants --------------------

#define LIMIT 8
#define SERVERS 2
#define THRESHOLD 15
#define SQTHRESHOLD 256

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

header_type switch_info_t {
    fields {
        swid: 32;
        flow_num: 32;
    }
}
header switch_info_t switch_info_head;

header_type meta_t {
    fields {
        temp : 32;

        server_flow1 : 32;
        server_flow2 : 32;
        switch_flow1 : 32;
        switch_flow2 : 32;
        switch_flow3 : 32;

        hash: 16;
        routing_port: 32;

        min_flow_len : 32;

        probe_bool : 32;
    }
}
metadata meta_t meta;

header_type intrinsic_metadata_t {
    fields {
        mcast_grp : 16;
        egress_rid : 16;
    }
}
metadata intrinsic_metadata_t intrinsic_metadata;

// ---------------------- Hashing ------------------

field_list flow_list {
    load_balancer_head.fid;
    load_balancer_head.subfid;
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
        1: interswitch;
        default: ingress;
    }
}

parser parse_head {
    extract(load_balancer_head);
    extract(switch_info_head);
    return ingress;
}

parser interswitch {
    extract(load_balancer_head);
    extract(switch_info_head);
    return ingress;
}

//------------------ Registers -----------------------

register total_flow_count_register {
    width: 32;
    instance_count: 5;
}

register flow_to_port_map_register {
    width: 32;
    instance_count: 65536;
}

// --------------------- Tables -------------------------------

// Update the switch_flow_count
table update_switch_flow_count_table {
    actions{
        update_switch_flow_count;
    }
    size: 1;
}

//Set destination tables
table get_server_flow_count_table{
    actions{
        get_server_flow_count;
    }
    size:1;
}

table set_server_dest_port_table{
    reads{
        meta.server_flow1 : exact;
        meta.server_flow2 : exact;
    }
    actions{
        set_server_dest_port;
    }
    size:SQTHRESHOLD;
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

// Updates flow_to_port_map_register on a SYN packet
table update_map_table {
    actions {
        update_map;
    }
    size: 1;
}

// Forwards packets
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

// Clears flow_to_port_map_register on a FIN packet
table clear_map_table {
    actions {
        clear_map;
    }
    size: 1;
}

// Update the server_flow_count
table update_flow_count_table {
    actions{
        update_flow_count;
    }
    size: 1;
}

// Send the update message regarding flow info to other switches
table update_min_flow_len1_table{
    actions{
        update_min_flow_len1;
    }
    size: 1;
}

table update_min_flow_len2_table{
    actions{
        update_min_flow_len2;
    }
    size: 1;
}


table send_update_table {
    actions{
        send_update;
    }
    size: 1;
}

table send_probe_table {
    actions{
        send_probe;
    }
    size: 1;
}

table set_probe_bool_table {
    actions{
        set_probe_bool;
    }
    size: 1;
}

// ---------------------------- Actions -----------------------

//Update switch flow count
action update_switch_flow_count() {
    register_write(total_flow_count_register,standard_metadata.ingress_port - 2, switch_info_head.flow_num);
}

//Set destination actions
action get_server_flow_count(){
    register_read(meta.server_flow1,total_flow_count_register,0);
    register_read(meta.server_flow2,total_flow_count_register,1);
}

action set_server_dest_port(flow_count,flow_dest){
    register_write(total_flow_count_register,flow_dest - 2, flow_count + 1);
    modify_field(standard_metadata.egress_spec,flow_dest);
}

action get_switch_flow_count(){
    register_read(meta.switch_flow1,total_flow_count_register,2);
    register_read(meta.switch_flow2,total_flow_count_register,3);
    register_read(meta.switch_flow3,total_flow_count_register,4);
}

action set_switch1_dest_port(){
    register_write(total_flow_count_register,2, meta.switch_flow1 + 1);
    modify_field(standard_metadata.egress_spec,4);
}

action set_switch2_dest_port(){
    register_write(total_flow_count_register,3, meta.switch_flow2 + 1);
    modify_field(standard_metadata.egress_spec,5);
}

action set_switch3_dest_port(){
    register_write(total_flow_count_register,4, meta.switch_flow3 + 1);
    modify_field(standard_metadata.egress_spec,6);
}

//Update mapping
action update_map() {
    modify_field_with_hash_based_offset(meta.hash, 0,
                                        flow_register_index, 65536);
    register_write(flow_to_port_map_register, meta.hash, standard_metadata.egress_spec);
}

//Forward
action forward() {
    modify_field_with_hash_based_offset(meta.hash, 0,
                                        flow_register_index, 65536);
    register_read(meta.routing_port, flow_to_port_map_register, meta.hash);
    modify_field(standard_metadata.egress_spec, meta.routing_port);
    modify_field(load_balancer_head.hash,meta.hash);
}

action _drop() {
    drop();
    //modify_field(standard_metadata.egress_spec,1);
}

//Clear mapping
action clear_map() {
    modify_field_with_hash_based_offset(meta.hash, 0,
                                        flow_register_index, 65536);
    register_write(flow_to_port_map_register, meta.hash, 0);
}

action update_flow_count() {
    register_read(meta.temp, total_flow_count_register, meta.routing_port-2);
    add_to_field(meta.temp,-1);
    register_write(total_flow_count_register,meta.routing_port-2, meta.temp);
}

action update_min_flow_len1(){
    modify_field(meta.min_flow_len, meta.server_flow1);
}

action update_min_flow_len2(){
    modify_field(meta.min_flow_len, meta.server_flow2);
}

field_list meta_list {
    meta;
    standard_metadata;
    intrinsic_metadata;
}

action send_update(){
    modify_field(load_balancer_head.preamble,2);
    modify_field(switch_info_head.swid,16);
    modify_field(switch_info_head.flow_num,meta.min_flow_len);
    modify_field(load_balancer_head._count, standard_metadata.ingress_port);
    modify_field(standard_metadata.egress_spec, standard_metadata.ingress_port);
}

action set_probe_bool(){
    modify_field(meta.probe_bool,1);
}

action send_probe(){
    clone_ingress_pkt_to_egress(standard_metadata.egress_spec,meta_list);
    modify_field(load_balancer_head.preamble, 1);
    modify_field(intrinsic_metadata.mcast_grp, 1);
}

//------------------------ Control Logic -----------------

control ingress {
    apply(get_server_flow_count_table);  
    if (load_balancer_head.preamble == 1){
        //send update
        if(meta.server_flow1 < meta.server_flow2){
            apply(update_min_flow_len1_table);
        }
        else{
            apply(update_min_flow_len2_table);
        }
        apply(send_update_table);
    }
    else if (load_balancer_head.preamble == 2){
        //get update
        apply(update_switch_flow_count_table);
    }
    else {
        //Start of flow
        if(load_balancer_head.syn == 1) {

            if(meta.server_flow1 < THRESHOLD or meta.server_flow2 < THRESHOLD){
                //Forwarding can be done locally
                apply(set_server_dest_port_table);

                //Take decision to send probe packet or not
                if ((meta.server_flow1 + meta.server_flow2)*10 > (LIMIT * 2 * THRESHOLD)){
                    apply(set_probe_bool_table);
                }
            }
            else{
                //Choose from switches
                apply(get_switch_flow_count_table);
                /*if (meta.switch_flow1 >= THRESHOLD and meta.switch_flow2 >= THRESHOLD and meta.switch_flow3 >= THRESHOLD){
                    drop();
                }*/
                if(meta.switch_flow1 <= meta.switch_flow2 and meta.switch_flow1 <= meta.switch_flow3){
                    apply(set_switch1_dest_port_table);
                }
                else if(meta.switch_flow2 <= meta.switch_flow1 and meta.switch_flow2 <= meta.switch_flow3){
                    apply(set_switch2_dest_port_table);
                }
                else if(meta.switch_flow3 <= meta.switch_flow1 and meta.switch_flow3 <= meta.switch_flow2){
                    apply(set_switch3_dest_port_table);
                }
            }

            //Update mapping
            apply(update_map_table);
        }

        //Forwarding
        apply(forwarding_table);

        if(meta.probe_bool == 1){
            apply(send_probe_table);
        }

        //End of flow
        if(load_balancer_head.fin == 1) {
            apply(clear_map_table);
            apply(update_flow_count_table);
        }
    }
}

control egress {
}
