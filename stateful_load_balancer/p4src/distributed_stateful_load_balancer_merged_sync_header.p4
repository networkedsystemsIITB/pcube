header_type sync_info_t {
    fields{
       _0 : 32;
   }
}

header sync_info_t sync_info;
header_type intrinsic_metadata_t {
    fields {
        mcast_grp : 16;
        egress_rid : 16;
    }
}
metadata intrinsic_metadata_t intrinsic_metadata;

field_list meta_list {
    standard_metadata;
    intrinsic_metadata;
}

