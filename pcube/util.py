########################################################
# 1. Constants required for the parser
########################################################

KEYWORDS = {
    'for'		:	'@pcube_for',
    'endfor'	:	'@pcube_endfor',
    'compare'	:	'@pcube_minmax',
    'endcompare':	'@pcube_endminmax',
    'case'		:	'@pcube_case',
    'endcase'	:	'@pcube_endcase',
    'sum'		:	'@pcube_sum',
    'bool'      :   '@pcube_cmp',
    'sync'      :   '@pcube_sync',
    'endsync'   :   '@pcube_endsync',
    'echo'      :   '@pcube_echo',
    'endecho'   :   '@pcube_endecho',
}

TOPO_DATA = None

SYNC_HEADER_FILE = "%s_sync_header.p4"
########################################################
# 2. Strings required for generating code
########################################################

### Used in <filename>_<switch_id>_sync.p4

TABLE_STRING = \
"table %s_info%d_table {\n\
    actions{\n\
        %s_info%d;\n\
    }\n\
    size: 1;\n\
}\n\n"

MODIFY_FIELD = \
"    modify_field(sync_info._%d,%s);\n"

ADD_HEADER = \
"   add_header(sync_info);\n"

SYNC_ACTION_START_STRING = \
"action %s_info%d() {\n\
    clone_ingress_pkt_to_egress(standard_metadata.egress_spec,meta_list);\n\
    modify_field(%s,%s);\n\
"
SYNC_ACTION_END_STRING = \
"    modify_field(intrinsic_metadata.mcast_grp, %d);\n\
}\n\n"

ECHO_ACTION_START_STRING = \
"action %s_info%d() {\n\
    modify_field(%s,%s);\n\
"
ECHO_ACTION_END_STRING = \
"    modify_field(standard_metadata.egress_spec, standard_metadata.ingress_port);\n\
}\n\n"

### Used in <filename>_sync_header.p4

HEADER_START_STRING = \
"header_type sync_info_t {\n\
    fields{\n\
"

HEADER_FNAME_STRING = \
"       _%d : 32;\n"

HEADER_END_STRING = \
"   }\n\
}\n\n"

HEADER = "header sync_info_t sync_info;\n"

INTRINSIC_METADATA = \
"header_type intrinsic_metadata_t {\n\
    fields {\n\
        mcast_grp : 16;\n\
        egress_rid : 16;\n\
    }\n\
}\n\
metadata intrinsic_metadata_t intrinsic_metadata;\n\n\
"

META_LIST = \
"field_list meta_list {\n\
    standard_metadata;\n\
    intrinsic_metadata;\n\
}\n\n"

### Used in <filename>_<switch_id>.p4

APPLY_SYNC_STRING = "%sapply(sync_info%d_table);\n"
APPLY_ECHO_STRING = "%sapply(echo_info%d_table);\n"

