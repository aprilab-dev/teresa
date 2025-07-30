from teresa.dump.lt1_dump_data import lt1_dump_data
from teresa.dump.lt1_dump_header2doris import lt1_dump_header2doris

from teresa.dump.bc3_dump_data import bc3_dump_data
from teresa.dump.bc3_dump_header2doris import bc3_dump_header2doris

from teresa.dump.bc4_dump_data import bc4_dump_data
from teresa.dump.bc4_dump_header2doris import bc4_dump_header2doris

dump_header2doris_funcs = {
    'LT1': lt1_dump_header2doris,
    'BC3': bc3_dump_header2doris,
    'BC4': bc4_dump_header2doris,
}

dump_data_funcs = {
    'LT1': lt1_dump_data,
    'BC3': bc3_dump_data,
    'BC4': bc4_dump_data,
}
