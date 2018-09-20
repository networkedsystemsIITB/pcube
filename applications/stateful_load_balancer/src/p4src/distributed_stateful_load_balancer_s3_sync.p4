table echo_info1_table {
    actions{
        echo_info1;
    }
    size: 1;
}

action echo_info1() {
    modify_field(load_balancer_head.preamble,2);
    modify_field(sync_info._0,meta.server_flow1 + meta.server_flow2);
   add_header(sync_info);
    modify_field(standard_metadata.egress_spec, standard_metadata.ingress_port);
}

table sync_info1_table {
    actions{
        sync_info1;
    }
    size: 1;
}

action sync_info1() {
    clone_ingress_pkt_to_egress(standard_metadata.egress_spec,meta_list);
    modify_field(load_balancer_head.preamble,1);
   add_header(sync_info);
    modify_field(intrinsic_metadata.mcast_grp, 3);
}

table sync_info2_table {
    actions{
        sync_info2;
    }
    size: 1;
}

action sync_info2() {
    clone_ingress_pkt_to_egress(standard_metadata.egress_spec,meta_list);
    modify_field(load_balancer_head.preamble,2);
    modify_field(sync_info._0,meta.server_flow1 + meta.server_flow2);
   add_header(sync_info);
    modify_field(intrinsic_metadata.mcast_grp, 3);
}

