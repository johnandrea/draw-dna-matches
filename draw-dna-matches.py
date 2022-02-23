#!/usr/local/bin/python3
import sys
import re
import readgedcom

# Output DNA matches in a tree view in Graphviz DOT format.
# Given a GEDCOM with people having an event of type defined below
# and an optional note containing the cM value.
# The person for whom the matches are compared should have a note or value
# beginning with 'Me,'
#
# Might hot handle the situation where the closest shared family between
# two people doesn't exist in the data.
# This code is released under the MIT License: https://opensource.org/licenses/MIT
# Copyright (c) 2022 John A. Andrea
#
# v2.0

# This is the name of the event of value
EVENT_NAME = 'dnamatch'

# within the event, 'note' or 'value'
EVENT_ITEM = 'note'

# lines to ancestors
line_colors = ['orchid', 'tomato', 'lightseagreen']
line_colors.extend( ['gold', 'royalblue', 'coral'] )
line_colors.extend( ['yellowgreen', 'chocolate', 'salmon'] )

# box containing a match person
box_color = 'lightgreen'

# multiple marriage outline
multi_marr_color = 'orange'


def remove_numeric_comma( s ):
    """ Given 1,234 1,234,567 and similar, remove the comma.
        Does the same for all such patterns in the string.
        Assuming anglo style numbers rather than euro style of 1.234,99 """

    comma_pattern = re.compile( r'\d,\d' )

    result = s

    # global replace count not working on this expression,
    # use a loop as a workaround

    while comma_pattern.search( result ):
          result = re.sub( r'^(.*\d),(\d.*)$', r'\1\2', result )

    return result


def extract_dna_cm( note ):
    """ Return the numeric cM value from the note which is either just
        a number or a number followed by "cM" or "cm" """

    a_number = re.compile( r'[0-9]' )
    all_numbers = re.compile( r'^[0-9]+$' )
    cm_count = re.compile( r'([0-9]+)\s*cm\W' )

    s = note.strip()

    result = ''

    if a_number.search( s ):
       s = remove_numeric_comma( s )
       if all_numbers.search( s ):
          result = s
       else:
          # append a space for a simpler regexp of the word ending
          match = cm_count.search( s.lower() + ' ' )
          if match:
             result = match.group(1)

    return result


def get_name( individual ):
    """ Return the name for the individual in the passed data section. """
    name = individual['name'][0]['value']
    # the standard unknown code is not good for svg output
    #if readgedcom.UNKNOWN_NAME in name: #string match problem with non-ascii?
    if '?' in name and '[' in name and ']' in name:
       name = 'unknown'
    return name.replace( '/', '' )


def get_fam_name( family, individuals ):
    """ Return the name of the two people in the padded
        family data section. """
    name = ''
    sep = ''
    for parent in ['wife','husb']:
        if parent in family:
           parent_id = family[parent][0]
           name += sep + get_name( individuals[parent_id] )
           sep = '\\n& '
    return name


def check_for_dna_event( individual ):
    """ Does the person in data section contain the
        desired dna event. Return a list with found or not. """
    result = [ False, '' ]
    if 'even' in individual:
       for event in individual['even']:
           if event['type'].lower() == EVENT_NAME.lower():
              if EVENT_ITEM in event:
                 result[0] = True
                 result[1] = event[EVENT_ITEM].strip()
              break
    return result


def get_ancestor_families( indi, individuals, families ):
    """ See the nested function. """

    def all_ancestor_families_of( gen, start, indi ):
        """ Return a dict of all the ancestors of the given individual.
            Format is collection of [fam_id] = number of genertions from start """
        result = dict()
        if 'famc' in individuals[indi]:
           fam = individuals[indi]['famc'][0]
           result[fam] = gen
           for parent in ['wife','husb']:
               if parent in families[fam]:
                  parent_id = families[fam][parent][0]
                  # prevent a loop
                  if parent_id != start:
                     result.update( all_ancestor_families_of( gen+1, start, parent_id ) )
        return result

    return all_ancestor_families_of( 1, indi, indi )


def find_ancestor_path( start, end_fam, individuals, families, path ):
    """ Return a list of the family ids from the start person to the end family.
        The list is in order of generations, i.e. the end family will be at the end
        of the list.
        Assuming that there are no loops in the families.
        Returned is a list of  [ found-flag, [ famid, famid, ..., end-famid ] ] """

    if 'famc' in individuals[start]:
       fam = individuals[start]['famc'][0]
       for parent in ['wife','husb']:
           if parent in families[fam]:
              parent_id = families[fam][parent][0]

              path.append( fam )

              if fam == end_fam:
                 return [ True, path ]

              # Try the next generation
              found = find_ancestor_path( parent_id, end_fam, individuals, families, path )
              if found[0]:
                 return found

              # This family doesn't lead to that ancestor
              path.pop()

    return [ False, path ]


def find_parents( the_indi, fam_data ):
    # return list of   [ parent, fam ], [ parent, fam ]
    results = []
    key = 'famc'
    if key in the_indi:
       fam = the_indi[key][0]
       for parent in ['husb','wife']:
           if parent in fam_data[fam]:
              results.append( [ fam_data[fam][parent][0], fam ] )
    return results


def does_fam_have_match( matches, family ):
    # Does the family contain a person which is a match
    result = False
    for parent in ['husb','wife']:
        if parent in family:
           if family[parent][0] in matches:
              result = True
              break
    return result


def make_dot_id( xref ):
    return xref.lower().replace('@','').replace('i','').replace('f','').replace('.','')

def make_fam_dot_id( xref ):
    return 'f' + make_dot_id( str(xref) )

def make_indi_dot_id( xref ):
    return 'i' + make_dot_id( str(xref) )

def begin_dot():
    """ Start of the DOT output file """
    print( 'digraph family {' )
    #print( 'node [shape=record];' )
    print( 'rankdir=LR;')


def end_dot():
    """ End of the DOT output file """
    print( '}' )


def dot_labels( individuals, families, matches, my_ancestors, fam_with_matches, people_in_paths ):
    """ Output a label for each person who appears in the graphs. """

    def output_label( dot_id, s, extra ):
        print( dot_id, '[label=' + s.replace("'",'.') + extra + '];' )

    def output_plain_family_label( fam, multiplied_marr ):
        text = ''
        sep = ''
        for parent in ['wife','husb']:
            if parent in families[fam]:
               parent_id = families[fam][parent][0]
               text += sep + get_name( individuals[parent_id] )
               sep = '\\n+ '
        options = ''
        if multiplied_marr:
           options = ', color=' + multi_marr_color
        output_label( make_fam_dot_id(fam), '"'+ text +'"', options )

    def output_match_family_label( fam, multiplied_marr ):
        text = '<\n<table cellpadding="2" cellborder="0" cellspacing="0" border="0">'
        sep = ''
        for parent in ['wife','husb']:
            if parent in families[fam]:
               parent_id = families[fam][parent][0]
               # add padding
               name = ' ' + sep + get_name( individuals[parent_id] ) + ' '
               tr = '\n<tr><td'
               if parent_id in matches:
                  td = tr + ' bgcolor="' + box_color + '">'
                  text += td + name + '</td></tr>'
                  text += td + matches[parent_id]['note'] + '</td></tr>'
               else:
                  text += tr + ' border="1">' + name + '</td></tr>'
               sep = '+ '
        text += '\n</table>\n>'
        options = ', shape="none"'
        if multiplied_marr:
           options += ', color=' + multi_marr_color
        output_label( make_fam_dot_id(fam), text, options )

    def output_indi_label( indi ):
        # note the escaped newlines
        text = get_name( individuals[indi] ) + '\\n' + matches[indi]['note']
        options = ', shape="record", style=filled, color=' + box_color
        output_label( make_indi_dot_id(indi), '"'+ text +'"', options )


    def find_families_of_multiple_marriages():
        results = []
        person_in_fams = dict()
        for indi in people_in_paths:
            person_in_fams[indi] = []
            key = 'fams'
            if key in individuals[indi]:
               for fam in individuals[indi][key]:
                   if fam in fam_with_matches:
                      person_in_fams[indi].append( fam )

        for indi in person_in_fams:
            if len( person_in_fams[indi] ) > 1:
               for fam in person_in_fams[indi]:
                   if fam not in results:
                      results.append( fam )

        return results

    multiple_marriages = find_families_of_multiple_marriages()

    already_used = []

    # names of the dna people
    for indi in matches:
        if indi not in already_used:
           already_used.append( indi )
           if indi not in people_in_paths:
              output_indi_label( indi )

        for fam in matches[indi]['path']:
            if fam not in already_used:
               already_used.append( fam )
               multiple_marr = fam in multiple_marriages
               if fam_with_matches[fam]:
                  output_match_family_label( fam, multiple_marr )
               else:
                  output_plain_family_label( fam, multiple_marr )

    # and for me
    for shared_fam in my_ancestors:
        for fam in my_ancestors[shared_fam]:
            if fam not in already_used:
               already_used.append( fam )
               multiple_marr = fam in multiple_marriages
               if fam_with_matches[fam]:
                  output_match_family_label( fam, multiple_marr )
               else:
                  output_plain_family_label( fam, multiple_marr )


def dot_connect( me, matches, my_paths, people_in_paths ):
    """ Output the links from one family to the next. """

    # if this many or more incoming edges, set a color on the edges
    n_to_color = 3

    # keep the routes from one family to the next
    # each one only once
    routes = dict()

    for indi in matches:
        # again, don't draw a person if they are in someone else's path
        if matches[indi]['path'] and indi not in people_in_paths:
           previous = make_indi_dot_id( indi )
           for ancestor in matches[indi]['path']:
               target = make_fam_dot_id( ancestor )
               route = (previous, target)
               routes[route] = ancestor
               previous = target

    for shared_fam in my_paths:
        # ok to route from me to first fam because it will be saved only once
        previous = make_indi_dot_id( me )
        for ancestor in my_paths[shared_fam]:
            target = make_fam_dot_id( ancestor )
            route = (previous, target)
            routes[route] = ancestor
            previous = target

    # count the number of connections into each family
    # so that the multiply connected can be coloured
    counts = dict()
    for route in routes:
        ancestor = routes[route]
        if ancestor not in counts:
           counts[ancestor] = 0
        counts[ancestor] += 1

    # assign the same color to the connection lines for the families
    # with multiple connections
    # and
    # loop through the colors to give a different color as each family matches
    ancestor_color = dict()
    n_colors = len( line_colors )
    c = n_colors + 1
    for ancestor in counts:
        if counts[ancestor] >= n_to_color:
           c = c + 1
           if c >= n_colors:
              c = 0
           ancestor_color[ancestor] = line_colors[c]

    # output the routes
    for route in routes:
        ancestor = routes[route]
        extra = ''
        if ancestor in ancestor_color:
           extra = ' [color=' + ancestor_color[ancestor] + ']'
        print( route[0] + ' -> ' + route[1] + extra + ';' )


# these are keys into the parsed sections of the returned data structure
i_key = readgedcom.PARSED_INDI
f_key = readgedcom.PARSED_FAM

opts = dict()
opts['display-gedcom-warnings'] = False

data = readgedcom.read_file( sys.argv[1], opts )

# people which do have the dna event
# matched[indi] = { note: the event text, shared: closest shared ancestor )
matched = dict()

# the id of the base dna match person
me = None

for indi in data[i_key]:
    result = check_for_dna_event( data[i_key][indi] )
    if result[0]:
       matched[indi] = dict()
       if result[1].lower().startswith( 'me,' ):
          matched[indi]['note'] = 'me'
          me = indi
       else:
          matched[indi]['note'] = extract_dna_cm( result[1] ) + ' cM'

if not me:
   print( 'Didnt find base person', file=sys.stderr )
   sys.exit()

ancestors = dict()
for indi in matched:
    ancestors[indi] = get_ancestor_families( indi, data[i_key], data[f_key] )

# how many generations do I have
max_gen = max( ancestors[me].values() )

# For each of the dna matched people,
# find the youngest ancestor which matches with me.
#
# Both people exist in the same tree so there must be a similar ancestor
# unless the dna match is noise. In this case the shared ancestor will be None.
#
# Finding shared ancestor person rather than shared ancestor family
# in order to skip half-cousins. Then in the display show only the people
# rather than families.

for indi in matched:
    if indi == me:
       continue

    found_match = None
    found_gen = max_gen + 1

    for ancestor_fam in ancestors[indi]:
        if ancestor_fam in ancestors[me]:
           my_generation = ancestors[me][ancestor_fam]
           if my_generation < found_gen:
              found_gen = my_generation
              found_match = ancestor_fam

    # the closest shared family
    matched[indi]['shared'] = found_match

# Find the path from each match to the closest shared family.
# Assuming only one such path for each matched person
# Adding the list in matched[indi]['path']

for indi in matched:
    matched[indi]['path'] = []
    if indi == me:
       continue
    top_ancestor_fam = matched[indi]['shared']
    if top_ancestor_fam:
       family_path = find_ancestor_path( indi, top_ancestor_fam, data[i_key], data[f_key], [] )
       if family_path[0]:
          matched[indi]['path'] = family_path[1]


# Find the paths from me to each of those shared ancestors

my_paths = dict()

shared_ancestors = dict()
for indi in matched:
    if indi == me:
       continue
    shared_ancestors[matched[indi]['shared']] = True

for ancestor_fam in shared_ancestors:
    family_path = find_ancestor_path( me, ancestor_fam, data[i_key], data[f_key], [] )
    if family_path[0]:
       my_paths[ancestor_fam] = family_path[1]

# Find families along those paths which contain a matched person
# value for each family is true or false.

families_with_matches = dict()

for indi in matched:
    if indi == me:
       continue
    for fam in matched[indi]['path']:
        if fam not in families_with_matches:
           families_with_matches[fam] = does_fam_have_match( matched, data[f_key][fam] )
for ancestor_fam in my_paths:
    for fam in my_paths[ancestor_fam]:
        if fam not in families_with_matches:
           families_with_matches[fam] = does_fam_have_match( matched, data[f_key][fam] )


# Find the people who are in the families in the paths
all_people_in_paths = []
for fam in families_with_matches:
    for parent in ['husb','wife']:
        if parent in data[f_key][fam]:
           all_people_in_paths.append( data[f_key][fam][parent][0] )

# Output to stdout

begin_dot()

dot_labels( data[i_key], data[f_key], matched, my_paths, families_with_matches, all_people_in_paths )
dot_connect( me, matched, my_paths, all_people_in_paths )

end_dot()
