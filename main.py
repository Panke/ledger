#!/usr/bin/env python

import sys
import os
import time
import re

from ledger import *

journal = Journal ()

add_config_option_handlers ()

args = process_arguments (sys.argv[1:])
config.use_cache = len (config.data_file) > 0
process_environment (os.environ, "LEDGER_")

if os.environ.has_key ("LEDGER"):
    process_option ("file", os.environ["LEDGER"])
if os.environ.has_key ("PRICE_HIST"):
    process_option ("price-db", os.environ["PRICE_HIST"])
if os.environ.has_key ("PRICE_EXP"):
    process_option ("price-exp", os.environ["PRICE_EXP"])

if len (args) == 0:
    option_help ()
    sys.exit (0)

command = args.pop (0);

if command == "balance" or command == "bal" or command == "b":
    command = "b"
elif command == "register" or command == "reg" or command == "r":
    command = "r"
elif command == "print" or command == "p":
    command = "p"
elif command == "entry":
    command = "e"
elif command == "equity":
    command = "E"
else:
    print "Unrecognized command:", command
    sys.exit (1)

text_parser = TextualParser ()
bin_parser  = BinaryParser ()
qif_parser  = QifParser ()

register_parser (text_parser)
register_parser (bin_parser)
register_parser (qif_parser)

parse_ledger_data (journal, text_parser, bin_parser)

config.process_options(command, args);

new_entry = None
if command == "e":
    new_entry = journal.derive_entry (args)
    if new_entry is None:
	sys.exit (1)

class FormatTransaction (TransactionHandler):
    last_entry = None
    output     = None

    def __init__ (self, fmt = None):
	if fmt is None:
	    self.formatter  = config.format
	    self.nformatter = config.nformat
	else:
	    try:
		i = string.index (fmt, '%/')
		self.formatter  = Format (fmt[: i])
		self.nformatter = Format (fmt[i + 2 :])
	    except ValueError:
		self.formatter  = Format (fmt)
		self.nformatter = None

	self.last_entry = None

	if config.output_file:
	    self.output = open(config.output_file, "w")
	else:
	    self.output = sys.stdout

	TransactionHandler.__init__ (self)

    def __del__ (self):
	if config.output_file:
	    self.output.close ()

    def flush (self):
	self.output.flush ()

    def __call__ (self, xact):
	if self.nformatter and xact.entry is self.last_entry:
	    self.output.write(self.nformatter.format(xact))
	else:
	    self.output.write(self.formatter.format(xact))
	    self.last_entry = xact.entry

handler = FormatTransaction()

if not (command == "b" or command == "E"):
    if config.display_predicate:
	handler = FilterTransactions(handler, config.display_predicate)

    handler = CalcTransactions(handler, config.show_inverted)

    if config.sort_order:
	handler = SortTransactions(handler, config.sort_order)

    if config.show_revalued:
	handler = ChangedValueTransactions(handler, config.show_revalued_only)

    if config.show_collapsed:
	handler = CollapseTransactions(handler);

    if config.show_subtotal:
	handler = SubtotalTransactions(handler)
    elif config.report_interval:
	handler = IntervalTransactions(handler, config.report_interval)
    elif config.days_of_the_week:
	handler = DowTransactions(handler)

if config.show_related:
    handler = RelatedTransactions(handler, config.show_all_related)

if config.predicate:
    handler = FilterTransactions(handler, config.predicate)

if 1:
    walk_entries (journal, handler)
else:
    # These for loops are equivalent to `walk_entries', but far slower
    for entry in journal:
	for xact in entry:
	    handler (xact)

handler.flush ()

if config.use_cache and config.cache_dirty and config.cache_file:
    write_binary_journal(config.cache_file, journal);
