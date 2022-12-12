# draw-dna-matches.py

A program that can help with viewing DNA matched family members.

## Features

- Output is a [Graphviz](https://graphviz.org) DOT file.
- Makes use of [readgedcom.py](https://github.com/johnandrea/readgedcom) library.

## Limitations

- Requires Python 3.6+
- Won't draw path if closest ancestor is not in the data file
- Double-cousins and other multiple relationships are shown in only one path
- Assumes that blood (biological) family connections are listed first in the data

## Installation

No installation process. Copy the program and the library.

## Input

The input is a GEDCOM file exported from a genealogy program. The key is that the DNA matches are marked in a custom event whose name is an input option. The match cM value will be extracted if found in that event's note field and will be
displayed below the person's name. The cM value in the note can be given as only a single number, or else it must be a number followed by cM. Such as "62", "123cm", "text 123 cm", "1,234 cM", etc. However "text 321 text" will not match.

An example of a relevant portion of the input file:

```
1 EVEN
2 TYPE dnamatch
2 NOTE matched at 732 cM
```

The matches are intended to be made against one person in the data file. That person
is identified by an event note which begins with the string "Me," or "me,".

```
1 EVEN
2 TYPE dnamatch
2 NOTE Me, matching others
```

By changing the internal program variable value of EVENT_ITEM to 'value' those sections should be similar to:

```
1 EVEN 732 cM
2 TYPE dnamatch
```

and

```
1 EVEN me, start person
2 TYPE dnamatch
```

## Options

event-name

The name of the custom event in which the data is stored. The examples above use "dnamatch".

gedcom-file

Full path to the input file.

--version 

Dispay the version number then exit

-- min=alue

Minimum match value (cM) to include in the output. Default 0.

--max=value

Maximum match value (cm) to include in the output. Default 5000.

--format=dot

Output as a DOT file for creating a display with Graphviz. This is the default.

or use
--format=gedcom

Output as a GEDCOM file for import into another program. A minimal amount of data is copied into the output. 

--relationship

Add relationship name (sibling, parent, 1C, 2C1R, etc.) to matches. Default is none.

--title="value"

Display a title on the output chart. Default is no title.

--reverse-arrows

Reverse the order of the arrows between parents and children. Default is from children to parents.

--orientation=direction

Set the orientatation of the diagram in the DOT file output. Default is "LR" for left-to-right.
Other choices are "TB" for top-to-bottom, plus "BT" (bottom-top), and "RL" (right-left).

--libpath=relative-path-to-library

The directory containing the readgedcom library, relative to the . Default is ".", the same location as this program file.


## Display

In the produced graphs, each dnamatch person will be shown in a green box. Any person which has multiple families will be in an orange bordered box. Any family with 3 or more incoming connections will have coloured input arrows.

## Example

![Example tree](test-data/test-family.png)

## Usage

```
draw-dna-matches.py  --relation  dnamatch  family.ged  >out.dot  2>out.err
graphviz -Tpng out.dot -o out.png
graphviz -Tsvg out.dot -o out.svg
```

Or to show only distant relatives
```
draw-dna-matches.py  --relation --max=800  dnamatch  family.ged  >out.dot  2>out.err
graphviz -Tpng out.dot -o out.png
graphviz -Tsvg out.dot -o out.svg
```

Or to make a new gedcom from the matches and common ancestors

```
draw-dna-matches.py  --format=gedcom  dnamatch  family.ged  >matches.ged
```

Example usage if readgedcom.py is in a parallel directory

```
draw-dna-matches.py --libpath=..\codecopy  dnamatch  family.ged  >out.dot  2>out.err
```

## Bug reports

This code is provided with neither support nor warranty.

### Future enhancements

- Print relationship along with DNA match value
- Handle non_ASCII names in a manner better for SVG output.
- Handle family matched above the tree top.
- Output to other formats (Cytoscape, etc.)
