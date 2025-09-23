from teresa.dump.lt1_dump_data import lt1_dump_data
from teresa.dump.lt1_dump_header2doris import lt1_dump_header2doris

from teresa.dump.bc_dump_data import bc_dump_data
from teresa.dump.bc_dump_header2doris import bc_dump_header2doris

dump_header2doris_funcs = {
    'LT1': lt1_dump_header2doris,
    'BC': bc_dump_header2doris,
}

dump_data_funcs = {
    'LT1': lt1_dump_data,
    'BC': bc_dump_data,
}
