#!/usr/bin/env python3

# Copyright 2018-present Akash Trehan Aniket Shirke
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

########################################################
# 1. Convert ip4 format to p4
########################################################

import sys
import os
import re
import json
from collections import OrderedDict
# For recognising the ???
from pyparsing import Word, alphas, nums, nestedExpr, Keyword, alphanums, Regex, White, Optional

import fileinput

# Kept a global for clarity on what all features are present
# and also prevent hardcoding of tokens in the code

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
    'mirror'    :   '@pcube_echo',
    'endmirror' :   '@pcube_endecho',
}

TOPO_DATA = None

TABLE_STRING = \
"table %s_info%d_table {\n\
    actions{\n\
        %s_info%d;\n\
    }\n\
    size: 1;\n\
}\n\n"

SYNC_ACTION_START_STRING = \
"action %s_info%d() {\n\
    clone_ingress_pkt_to_egress(standard_metadata.egress_spec,meta_list);\n\
    modify_field(%s,%s);\n\
"
MIRROR_ACTION_START_STRING = \
"action %s_info%d() {\n\
    modify_field(%s,%s);\n\
"

MODIFY_FIELD = \
"    modify_field(sync_info._%d,%s);\n"

SYNC_ACTION_END_STRING = \
"    modify_field(intrinsic_metadata.mcast_grp, %d);\n\
}\n\n"

MIRROR_ACTION_END_STRING = \
"    modify_field(standard_metadata.egress_spec, standard_metadata.ingress_port);\n\
}\n\n"

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

APPLY_SYNC_STRING = "%sapply(sync_info%d_table);\n"
APPLY_MIRROR_STRING = "%sapply(mirror_info%d_table);\n"

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

class p4_code_generator():

    def __init__(self, switch_id, src, dest, filename):
        self.switch_id = switch_id
        self.string_id = 's%d'%switch_id
        self.src = src
        self.destfor = dest + ".for"
        self.destcmp = dest + ".cmp"
        self.destsum = dest + ".sum"
        self.destbool = dest + ".bool"
        self.destsync = filename + "_s%d_sync.p4"%self.switch_id
        self.sync_header = filename + "_sync_header.p4"
        self.dest = dest
        self.tempfiles = [
            self.destfor,
            self.destfor + ".bak",
            self.destcmp,
            self.destsum,
            self.destbool
        ]

        self.constants = {
            "MCAST_GRP": switch_id
        }

        self.sync_id = 0
        self.mirror_id = 0

    def expand(self):
        os.system('rm -f %s' % self.destsync)
        self.expand_for()
        self.replace_constants()
        self.expand_compare()
        self.expand_sum()
        self.expand_bool()
        self.expand_sync()
        self.generate_commands_template()
        for f in self.tempfiles:
            os.system('rm -f %s' % f)

    # Replaces the ip4 for loop format by sequential p4 code
    def roll_out_forloop(self,content,iter_var,dfile,start,end,step):
        # For replacing all occurances of the loop variable in the code.
        replacement = '$%s' % iter_var

        for i in range(start,end,step):
            dfile.write(content.replace(replacement,str(i)))

    # Recognises all for loops present in the code along with their parameters
    # Nesting of loops not supported since it's not a common feature required in P4 programming
    # TODO: Can use pyparsing code just like in all other functions
    def expand_for(self):
        # Recognises if we are in a for loop
        active_for = False
        # The iteration variable
        iter_var = None
        # range(start, end, step)
        start,end,step = None,None,None
        # Content of the loop
        content = ""
        #include header
        header_included = False

        sfile = open(self.src,'r')
        dfile = open(self.destfor,'w')

        # Can read in any #define constant and replaces them if present as a parameter for `for` loop
        # For e.g. Number of servers

        # Loop through ip4 source
        for row in sfile:
            # Collect CONSTANTS
            if not header_included:
                dfile.write("#include \"%s\"\n"%self.sync_header.split('/')[1])
                dfile.write("#include \"%s\"\n"%self.destsync.split('/')[1])
                header_included = True

            if '#define' in row:
                _, var_name, val = row.split()
                define_string = "#define %s %d\n"
                if var_name in self.constants :
                    val = self.constants[var_name]
                elif var_name in TOPO_DATA["topo_stats"][self.string_id]:
                    val = TOPO_DATA["topo_stats"][self.string_id][var_name]
                else:
                    if var_name == "SERVERPLUSONE":
                        val = self.constants["SERVERS"] + 1
                    elif var_name == "SERVERMINUSONE":
                        val = self.constants["SERVERS"] - 1
                    elif var_name == "SWITCHPLUSONE":
                        val = self.constants["SWITCHES"] + 1
                    elif var_name == "SWITCHMINUSONE":
                        val = self.constants["SWITCHES"] - 1
                    elif var_name == "SWITCHPLUSSERVER":
                        val = self.constants["SERVERS"] + self.constants["SWITCHES"]

                self.constants[var_name] = int(val)
                # dfile.write(define_string%(var_name,int(val)))

            # If we are entering a for loop or already in one
            elif active_for or KEYWORDS['for'] in row:
                # If starting a for loop
                if KEYWORDS['for'] in row:
                    active_for = True
                    tokens = row.split()
                    # Get the lexeme used as iteration variable
                    iter_var = re.search(r'\((.*)\)',tokens[1]).group(1)
                    #
                    res = re.search(r'\((.*),(.*),(.*)\)',tokens[2].rstrip('\n'))
                    try:
                        start, end, step = int(res.group(1)), int(res.group(2)), int(res.group(3))
                    except:
                        start, end, step = int(res.group(1)), self.constants[res.group(2)], int(res.group(3))

                elif KEYWORDS['endfor'] in row:
                    # print(content)
                    self.roll_out_forloop(content,iter_var,dfile,start,end,step)
                    active_for = False
                    content = ""
                else:
                    content += row
            else:
                dfile.write(row)

        sfile.close()
        dfile.close()
        self.replace_constants()

    def replace_constants(self):
        for key, value in self.constants.items():
            with fileinput.FileInput(self.destfor, inplace=True, backup='.bak') as file:
                for line in file:
                    print(line.replace(key, str(value)), end='')


    def roll_out_compare(self,varlist, op, dfile):
        var_keys = list(varlist.keys())
        condition = {}
        final = ''
        a = varlist[var_keys[0]]
        spaces = ' '*(len(a) - len(a.lstrip(' ')) - 4)

        if len(var_keys) == 1:
            final = '%s%s' % (spaces,varlist[var_keys[0]].rstrip('\n'))
        else:
            for i in var_keys:
                cond = ''
                for j in var_keys:
                    if j != i:
                        cond += "%s %s %s" % (i, op, j)
                        if (i != var_keys[-1] and j != var_keys[-1]) or (i == var_keys[-1] and j != var_keys[-2]):
                            cond += ' and '
                condition[i] = cond

                if i == var_keys[0]:
                    final += '%sif(%s) {\n%s\n%s}\n' % (spaces, cond, varlist[i].rstrip('\n'), spaces)
                else:
                    final += '%selse if(%s) {\n%s\n%s}\n' % (spaces, cond, varlist[i].rstrip('\n'), spaces)

        dfile.write(final)

    def expand_compare(self):
        sfile = open(self.destfor, 'r')
        dfile = open(self.destcmp, 'w')

        compare_format = Keyword(KEYWORDS['compare']) + '(' + Regex(r'[^\s\(\)]*')('op') + ')'
        case_var_format = Word(alphas+"_", alphanums+"_"+".")('var')
        case_format = Keyword(KEYWORDS['case']) + case_var_format + ":"

        for line in sfile:
            if KEYWORDS['compare'] in line:
                # import pdb; pdb.set_trace()
                res = compare_format.parseString(line)
                op = res.op
                varlist = OrderedDict()
                while True:
                    l = sfile.readline()
                    # import pdb; pdb.set_trace()
                    if KEYWORDS['endcompare'] in l:
                        break
                    elif KEYWORDS['case'] in l:
                        # import pdb; pdb.set_trace()
                        res = case_format.parseString(l)
                        var = res.var
                        varlist[var] = ''
                        lcase = sfile.readline()
                        content = ''
                        while KEYWORDS['endcase'] not in lcase:
                            content += lcase
                            lcase = sfile.readline()
                        varlist[var] = content
                self.roll_out_compare(varlist, op, dfile)
            else:
                dfile.write(line)

        sfile.close()
        dfile.close()

    def expand_sum(self):
        sfile = open(self.destcmp, 'r')
        dfile = open(self.destsum, 'w')

        sum_format = Keyword(KEYWORDS['sum']) + '(' + Word(nums)("start") + "," + Word(nums)("end") + "," + Word(nums)("jump") + ')' \
                        + '(' + Regex(r'[^\s\(\)]*')("var") + ')'
        line_sum_format = Regex(r'[^\@]*')("before") + sum_format + Regex(r'[^\@]*')("after")

        for line in sfile:
            if KEYWORDS['sum'] in line:
                # import pdb; pdb.set_trace()
                res = line_sum_format.parseString(line)
                start = int(res.start)
                end = int(res.end)
                jump = int(res.jump)
                var = res.var

                replacement = res.before
                for i in range(start, end,jump):
                    replacement += var.replace("$i", str(i)) + " + "
                replacement = replacement[:-3] + res.after

                #FIX MEE !!!
                if len(res.after.split()) == 0: replacement += "\n"
                dfile.write(replacement)
            else:
                dfile.write(line)

        sfile.close()
        dfile.close()

    def expand_bool(self):
        sfile = open(self.destsum, 'r')
        dfile = open(self.destbool, 'w')

        bool_format = Keyword(KEYWORDS['bool']) + '(' + Word(nums)("start") + "," + Word(nums)("end") + ","      + Word(nums)("jump") + ')' + '(' + Regex(r'[^\s\(\)]*')('op') + ')' + '(' + Regex(r'[^\s\(\),]*')("logical_op") + ')' + '(' + Regex(r'[^\s\(\),]*')("var") + "," + Regex(r'[^\s\(\),]*')("operand") + ')'
        line_bool_format = Regex(r'[^\@]*')("before") + \
            bool_format + Regex(r'[^\@]*')("after")

        for line in sfile:
            if KEYWORDS['bool'] in line:
                # import pdb; pdb.set_trace()
                res = line_bool_format.parseString(line)
                start = int(res.start)
                end = int(res.end)
                jump = int(res.jump)
                logical_op = res.logical_op
                var = res.var
                operand = res.operand
                op = res.op

                replacement = res.before
                for i in range(start, end, jump):
                    replacement +=  "%s %s %s %s " % (var.replace("$i", str(i)), op, operand, logical_op)
                replacement = replacement[:-2 - len(logical_op)] + res.after
                dfile.write(replacement)
            else:
                dfile.write(line)

        sfile.close()
        dfile.close()

    def write_sync_action(self, fields, sync_id, field_name, val):
        sfile = open(self.destsync, 'a')

        globals()["sync_fields_count"] = max(len(fields), globals()["sync_fields_count"])

        sfile.write(TABLE_STRING%("sync",sync_id,"sync",sync_id))
        sfile.write(SYNC_ACTION_START_STRING%("sync",sync_id,field_name,val))

        for i in range(len(fields)):
            sfile.write(MODIFY_FIELD%(i,fields[i]))

        sfile.write(SYNC_ACTION_END_STRING%self.constants["MCAST_GRP"])
        sfile.close()

    def write_mirror_action(self, fields, mirror_id, field_name, val):
        sfile = open(self.destsync, 'a')

        globals()["sync_fields_count"] = max(len(fields), globals()["sync_fields_count"])

        sfile.write(TABLE_STRING%("mirror",mirror_id,"mirror",mirror_id))
        sfile.write(MIRROR_ACTION_START_STRING%("mirror",mirror_id,field_name,val))

        for i in range(len(fields)):
            sfile.write(MODIFY_FIELD%(i,fields[i]))

        sfile.write(MIRROR_ACTION_END_STRING)
        sfile.close()

    def expand_sync(self):
        sfile = open(self.destbool, 'r')
        dfile = open(self.dest, 'w')

        sync_format = Keyword(KEYWORDS['sync']) + '(' + Regex(r'[_a-zA-Z]*')("header_name") + "." + Regex(r'[^\s\(\),]*')("field") + "," + Word(nums)("val") + ')'
        mirror_format = Keyword(KEYWORDS['mirror']) + '(' + Regex(r'[_a-zA-Z]*')("header_name") + "." + Regex(r'[^\s\(\),]*')("field") + "," + Word(nums)("val") + ')'

        active_sync, active_mirror = False, False
        fields, field_name, val = [], None, None

        for line in sfile:
            if KEYWORDS['sync'] in line:
                res = sync_format.parseString(line)
                field_name, val = res.header_name + '.' + res.field, res.val
                active_sync = True
                self.sync_id += 1

            elif KEYWORDS['mirror'] in line:
                res = mirror_format.parseString(line)
                field_name, val = res.header_name + '.' + res.field, res.val
                active_mirror = True
                self.mirror_id += 1

            elif KEYWORDS['endsync'] in line:
                active_sync = False
                self.write_sync_action(fields,self.sync_id, field_name, val)
                fields = []
                indent = line[:-len(line.lstrip())]
                dfile.write(APPLY_SYNC_STRING%(indent,self.sync_id))

            elif KEYWORDS['endmirror'] in line:
                active_mirror = False
                self.write_mirror_action(fields,self.mirror_id, field_name, val)
                fields = []
                indent = line[:-len(line.lstrip())]
                dfile.write(APPLY_MIRROR_STRING%(indent,self.mirror_id))

            elif active_sync or active_mirror:
                fields.append(line.strip())

            else:
                dfile.write(line)
        sfile.close()
        dfile.close()

    def generate_commands_template_helper(self,sfile,dfile):
        open_brac = Optional(White()) + "{" + Optional(White())
        close_brac = Optional(White()) + "}" + Optional(White())
        actions_format = Keyword('actions') + open_brac + Word(alphas + "_", alphanums+"_")('default_action') \
                + ";" + Regex(r'[^\}\{]*') + close_brac
        reads_format = Keyword('reads') + open_brac + Regex(r'[^\}\{]*') + close_brac
        table_format = Keyword('table') + Word(alphas+"_", alphanums+"_")('table_name') + open_brac \
                + Optional(reads_format) + actions_format + \
                Optional(reads_format) + Regex(r'[^\}\{]*') + close_brac
        sfile_str = sfile.read()
        res = table_format.searchString(sfile_str)

        for table in res:
            dfile.write('table_set_default %s %s\n' % (table.table_name, table.default_action))

    def generate_commands_template(self):
        sfile = open(self.dest, 'r')
        dfile = open('commands_template_merged_%s.txt'%self.string_id, 'w')

        self.generate_commands_template_helper(sfile,dfile)
        #Hardcoded limits temporarily
        dfile.write('table_add get_limits_table get_limits => 20 80\n')
        
        sfile.close()
        dfile.close()
        
        sfile = open(self.destsync, 'r')
        dfile = open('sync_commands_%s.txt'%self.string_id, 'w')
        
        self.generate_commands_template_helper(sfile,dfile)
        
        sfile.close()
        dfile.close()


def generate_sync_header(filename):
    sfile = open(filename+"_sync_header.p4",'w')

    sfile.write(HEADER_START_STRING)
    for i in range(globals()["sync_fields_count"]):
        sfile.write(HEADER_FNAME_STRING%i)
    sfile.write(HEADER_END_STRING)
    sfile.write(HEADER)

    sfile.write(INTRINSIC_METADATA)
    sfile.write(META_LIST)
    sfile.close()

def get_topo_data():
    with open('topo.json','r') as f:
        data = json.load(f)
    return data

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Format: python3 %s <filename>.ip4" % sys.argv[0])
        sys.exit()

    TOPO_DATA = get_topo_data()
    num_switches = TOPO_DATA["nb_switches"]

    src = sys.argv[1]

    filename = src[:-4]

    globals()["sync_fields_count"] = 0

    for i in range(1, num_switches + 1):
        dest = "%s_s%d.p4" % (filename,i)
        code_gen = p4_code_generator(i,src,dest,filename)
        code_gen.expand()

    generate_sync_header(filename)
