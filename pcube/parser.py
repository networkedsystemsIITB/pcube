#!/usr/bin/env python3

########################################################
# 1. Convert ip4 format to p4
########################################################

import sys
import os
import re
import json
import fileinput
from collections import OrderedDict
from pyparsing import Word, alphas, nums, nestedExpr, Keyword, alphanums, Regex, White, Optional

from util import *

class p4_code_generator():

    def __init__(self, switch_id, src, dest, filename, folder, commands_folder):
        self.switch_id = switch_id
        self.string_id = 's%d'%switch_id
        self.src = src
        self.destfor = dest + ".for"
        self.destcmp = dest + ".cmp"
        self.destsum = dest + ".sum"
        self.destbool = dest + ".bool"
        self.destsync = folder + filename + "_s%d_sync.p4"%self.switch_id
        self.sync_header_file = SYNC_HEADER_FILE % (folder + filename)
        self.folder = folder
        self.commands_folder = commands_folder
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
        self.echo_id = 0

    def expand(self):
        os.system('rm -f %s' % self.destsync)
        self.expand_for()
        self.replace_constants()
        self.expand_minmax()
        self.expand_sum()
        self.expand_cmp()
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
                dfile.write("#include \"%s\"\n"%self.sync_header_file.split('/')[-1])
                dfile.write("#include \"%s\"\n"%self.destsync.split('/')[-1])
                header_included = True

            if '#define' in row:
                _, var_name, val = row.split()
                define_string = "#define %s %d\n"
                if var_name in self.constants :
                    val = self.constants[var_name]
                elif var_name in TOPO_DATA["topo_stats"][self.string_id]:
                    val = TOPO_DATA["topo_stats"][self.string_id][var_name]
                
                self.constants[var_name] = int(val)

            # If we are entering a for loop or already in one
            elif active_for or KEYWORDS['for'] in row:
                # If starting a for loop
                if KEYWORDS['for'] in row:
                    active_for = True
                    tokens = row.split()
                    # Get the lexeme used as iteration variable
                    iter_var = re.search(r'\((.*)\)',tokens[1]).group(1)
                    res = re.search(r'\((.*),(.*),(.*)\)',tokens[2].rstrip('\n'))
                    try:
                        start, end, step = int(res.group(1)), int(res.group(2)), int(res.group(3))
                    except:
                        start, end, step = int(res.group(1)), self.constants[res.group(2)], int(res.group(3))

                elif KEYWORDS['endfor'] in row:
                    self.roll_out_forloop(content,iter_var,dfile,start,end,step)
                    active_for = False
                    content = ""
                else:
                    content += row
            else:
                dfile.write(row)

        sfile.close()
        dfile.close()

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

    def expand_minmax(self):
        sfile = open(self.destfor, 'r')
        dfile = open(self.destcmp, 'w')

        compare_format = Keyword(KEYWORDS['compare']) + '(' + Regex(r'[^\s\(\)]*')('op') + ')'
        case_var_format = Word(alphas+"_", alphanums+"_"+".")('var')
        case_format = Keyword(KEYWORDS['case']) + case_var_format + ":"

        for line in sfile:
            if KEYWORDS['compare'] in line:
                res = compare_format.parseString(line)
                op = res.op
                varlist = OrderedDict()
                while True:
                    l = sfile.readline()
                    if KEYWORDS['endcompare'] in l:
                        break
                    elif KEYWORDS['case'] in l:
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
                res = line_sum_format.parseString(line)
                start = int(res.start)
                end = int(res.end)
                jump = int(res.jump)
                var = res.var

                replacement = res.before
                for i in range(start, end,jump):
                    replacement += var.replace("$i", str(i)) + " + "
                replacement = replacement[:-3] + res.after

                #FIX ME!
                if len(res.after.split()) == 0: replacement += "\n"
                
                dfile.write(replacement)
            else:
                dfile.write(line)

        sfile.close()
        dfile.close()

    def expand_cmp(self):
        sfile = open(self.destsum, 'r')
        dfile = open(self.destbool, 'w')

        bool_format = Keyword(KEYWORDS['bool']) + '(' + Word(nums)("start") + "," + Word(nums)("end") + ","      + Word(nums)("jump") + ')' + '(' + Regex(r'[^\s\(\)]*')('op') + ')' + '(' + Regex(r'[^\s\(\),]*')("logical_op") + ')' + '(' + Regex(r'[^\s\(\),]*')("var") + "," + Regex(r'[^\s\(\),]*')("operand") + ')'
        line_bool_format = Regex(r'[^\@]*')("before") + \
            bool_format + Regex(r'[^\@]*')("after")

        for line in sfile:
            if KEYWORDS['bool'] in line:
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

        sfile.write(ADD_HEADER)
        sfile.write(SYNC_ACTION_END_STRING%self.constants["MCAST_GRP"])
        sfile.close()

    def write_echo_action(self, fields, echo_id, field_name, val):
        sfile = open(self.destsync, 'a')

        globals()["sync_fields_count"] = max(len(fields), globals()["sync_fields_count"])

        sfile.write(TABLE_STRING%("echo",echo_id,"echo",echo_id))
        sfile.write(ECHO_ACTION_START_STRING%("echo",echo_id,field_name,val))

        for i in range(len(fields)):
            sfile.write(MODIFY_FIELD%(i,fields[i]))

        sfile.write(ADD_HEADER)
        sfile.write(ECHO_ACTION_END_STRING)
        sfile.close()

    def expand_sync(self):
        sfile = open(self.destbool, 'r')
        dfile = open(self.dest, 'w')

        sync_format = Keyword(KEYWORDS['sync']) + '(' + Regex(r'[_a-zA-Z]*')("header_name") + "." + Regex(r'[^\s\(\),]*')("field") + "," + Word(nums)("val") + ')'
        echo_format = Keyword(KEYWORDS['echo']) + '(' + Regex(r'[_a-zA-Z]*')("header_name") + "." + Regex(r'[^\s\(\),]*')("field") + "," + Word(nums)("val") + ')'

        active_sync, active_echo = False, False
        fields, field_name, val = [], None, None

        for line in sfile:
            if KEYWORDS['sync'] in line:
                res = sync_format.parseString(line)
                field_name, val = res.header_name + '.' + res.field, res.val
                active_sync = True
                self.sync_id += 1

            elif KEYWORDS['echo'] in line:
                res = echo_format.parseString(line)
                field_name, val = res.header_name + '.' + res.field, res.val
                active_echo = True
                self.echo_id += 1

            elif KEYWORDS['endsync'] in line:
                active_sync = False
                self.write_sync_action(fields,self.sync_id, field_name, val)
                fields = []
                indent = line[:-len(line.lstrip())]
                dfile.write(APPLY_SYNC_STRING%(indent,self.sync_id))

            elif KEYWORDS['endecho'] in line:
                active_echo = False
                self.write_echo_action(fields,self.echo_id, field_name, val)
                fields = []
                indent = line[:-len(line.lstrip())]
                dfile.write(APPLY_ECHO_STRING%(indent,self.echo_id))

            elif active_sync or active_echo:
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
        dfile = open('%scommands_template_%s.txt'%(self.commands_folder, self.string_id), 'w')

        self.generate_commands_template_helper(sfile,dfile)
        
        sfile.close()
        dfile.close()
        
        sfile = open(self.destsync, 'r')
        dfile = open('%ssync_commands_%s.txt'%(self.commands_folder, self.string_id), 'w')
        
        self.generate_commands_template_helper(sfile,dfile)
        
        sfile.close()
        dfile.close()


def generate_sync_header(folder, filename):
    sfile = open(SYNC_HEADER_FILE % (folder + filename) ,'w')

    sfile.write(HEADER_START_STRING)
    for i in range(globals()["sync_fields_count"]):
        sfile.write(HEADER_FNAME_STRING%i)
    sfile.write(HEADER_END_STRING)
    sfile.write(HEADER)

    sfile.write(INTRINSIC_METADATA)
    sfile.write(META_LIST)
    sfile.close()

def get_topo_data(topo_file):
    with open(topo_file,'r') as f:
        data = json.load(f)
    return data

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Format: python3 %s <filename>.ip4 <topology>.json" % sys.argv[0])
        sys.exit()

    ### Read in topology information
    topo_file = sys.argv[2]
    TOPO_DATA = get_topo_data(topo_file)
    num_switches = TOPO_DATA["nb_switches"]

    src = sys.argv[1]
    ip4_file = src.split('/')[-1]
    filename = ip4_file.split('.')[0]
    p4src_folder = src[0:-len(ip4_file)] + 'p4src/'
    commands_folder = src[0:-len(ip4_file)] + 'commands/'

    globals()["sync_fields_count"] = 0

    for i in range(1, num_switches + 1):
        dest = "%s%s_s%d.p4" % (p4src_folder,filename,i)
        code_gen = p4_code_generator(i,src,dest,filename,p4src_folder,commands_folder)
        code_gen.expand()

    generate_sync_header(p4src_folder, filename)
