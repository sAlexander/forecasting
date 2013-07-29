import psycopg2
import numpy as np
from struct import pack
from io import BytesIO
from datetime import datetime


def prepare_text(dat):
    cpy = BytesIO()
    for row in dat:
        cpy.write('\t'.join([repr(x) for x in row]) + '\n')
    return(cpy)

def prepare_binary(dat):
    pgcopy_dtype = [('num_fields','>i2')]
    for field, dtype in dat.dtype.descr:
        pgcopy_dtype += [(field + '_length', '>i4'),
                         (field, dtype.replace('<', '>'))]
    pgcopy = np.empty(dat.shape, pgcopy_dtype)
    pgcopy['num_fields'] = len(dat.dtype)
    for i in range(len(dat.dtype)):
        field = dat.dtype.names[i]
        pgcopy[field + '_length'] = dat.dtype[i].alignment
        pgcopy[field] = dat[field]
    cpy = BytesIO()
    cpy.write(pack('!11sii', b'PGCOPY\n\377\r\n\0', 0, 0))
    cpy.write(pgcopy.tostring())  # all rows
    cpy.write(pack('!h', -1))  # file trailer
    return(cpy)

def time_pgcopy(dat, table, binary):
    print('Processing copy object for ' + table)
    tstart = datetime.now()
    if binary:
        cpy = prepare_binary(dat)
    else:  # text
        cpy = prepare_text(dat)
    tendw = datetime.now()
    print('Copy object prepared in ' + str(tendw - tstart) + '; ' +
          str(cpy.tell()) + ' bytes; transfering to database')
    cpy.seek(0)
    if binary:
        curs.copy_expert('COPY ' + table + ' FROM STDIN WITH BINARY', cpy)
    else:  # text
        curs.copy_from(cpy, table)
    conn.commit()
    tend = datetime.now()
    print('Database copy time: ' + str(tend - tendw))
    print('        Total time: ' + str(tend - tstart))
    return

if __name__ == '__main__':
    conn = psycopg2.connect("dbname=test user=salexander")
    curs = conn.cursor()

    # NumPy record array
    shape = (7, 2000, 500)
    print('Generating data with %i rows, %i columns' % (shape[1]*shape[2], shape[0]))

    dtype = ([('id', 'i4'), ('node', 'i4'), ('ts', 'i2')] +
            [('s' + str(x), 'f4') for x in range(shape[0])])
    data = np.empty(shape[1]*shape[2], dtype)
    data['id'] = np.arange(shape[1]*shape[2]) + 1
    data['node'] = np.tile(np.arange(shape[1]) + 1, shape[2])
    data['ts'] = np.repeat(np.arange(shape[2]) + 1, shape[1])
    data['s0'] = np.random.rand(shape[1]*shape[2]) * 100
    prv = 's0'
    for nxt in data.dtype.names[4:]:
        data[nxt] = data[prv] + np.random.rand(shape[1]*shape[2]) * 10
        prv = nxt

    time_pgcopy(data, 'num_data_text', binary=False)
    time_pgcopy(data, 'num_data_binary', binary=True)
