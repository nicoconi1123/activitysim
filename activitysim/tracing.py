# ActivitySim
# See full license in LICENSE.txt.

import os
import sys
import logging
import logging.config

import yaml

import numpy as np
import pandas as pd
import orca

# Configurations
TRACE_LOGGER = 'activitysim.trace'
ASIM_LOGGER = 'activitysim'
CSV_FILE_TYPE = 'csv'
LOGGING_CONF_FILE_NAME = 'logging.yaml'

# Tracers
tracers = {}


def delete_csv_files(output_dir):
    """
    Delete CSV files

    Parameters
    ----------
    output_dir: str
        Directory of trace output CSVs

    Returns
    -------
    Nothing
    """
    for the_file in os.listdir(output_dir):
        if the_file.endswith(CSV_FILE_TYPE):
            file_path = os.path.join(output_dir, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)


def log_file_path(name):
    """
    For use in logging.yaml tag to inject log file path

    filename: !!python/object/apply:activitysim.defaults.tracing.log_file_path ['asim.log']

    Parameters
    ----------
    name: str
        output folder name

    Returns
    -------
    f: str
        output folder name
    """
    output_dir = orca.get_injectable('output_dir')
    f = os.path.join(output_dir, name)
    return f


def config_logger(custom_config_file=None, basic=False):
    """
    Configure logger

    if log_config_file is not supplied then look for conf file in configs_dir

    if not found use basicConfig

    Parameters
    ----------
    custom_config_file: str
        custom config filename
    basic: boolean
        basic setup

    Returns
    -------
    Nothing
    """
    log_config_file = None

    if custom_config_file and os.path.isfile(custom_config_file):
        log_config_file = custom_config_file
    elif not basic:
        # look for conf file in configs_dir
        configs_dir = orca.get_injectable('configs_dir')
        default_config_file = os.path.join(configs_dir, "configs", LOGGING_CONF_FILE_NAME)
        if os.path.isfile(default_config_file):
            log_config_file = default_config_file

    if log_config_file:
        with open(log_config_file) as f:
            config_dict = yaml.load(f)
            config_dict = config_dict['logging']
            config_dict.setdefault('version', 1)
            logging.config.dictConfig(config_dict)
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    logger = logging.getLogger(ASIM_LOGGER)

    if custom_config_file and not os.path.isfile(custom_config_file):
        logger.error("#\n#\n#\nconfig_logger could not find conf file '%s'" % custom_config_file)

    if log_config_file:
        logger.info("Read logging configuration from: %s" % log_config_file)
    else:
        print "Configured logging using basicConfig"
        logger.info("Configured logging using basicConfig")

    output_dir = orca.get_injectable('output_dir')
    logger.info("Deleting files in output_dir %s" % output_dir)
    delete_csv_files(output_dir)


def get_tracer(name=TRACE_LOGGER):
    """
    Get tracer

    Parameters
    ----------
    name: str
        tracer name

    Returns
    -------
    tracer: Tracer
        tracer
    """
    tracer = logging.getLogger(name)

    if (len(tracer.handlers) == 0):

        tracer.propagate = False
        tracer.setLevel(logging.INFO)

        file_path = log_file_path('%s.log' % name)
        fileHandler = logging.FileHandler(filename=file_path, mode='w')
        tracer.addHandler(fileHandler)

        logger = logging.getLogger(ASIM_LOGGER)
        logger.info("Initialized tracer %s fileHandler %s" % (name, file_path))

    return tracer


def info(name=__name__, message=None, log=True):
    """
    write message to logger and/or tracer if household tracing enabled

    Parameters
    ----------
    logger: logger
        standard logger to write to (or not if None)
    message:
        logging message to write to logger and/or tracer

    Returns
    -------
    Nothing
    """
    if log:
        logging.getLogger(name).info(message)

    if orca.get_injectable('enable_trace_log'):
        get_tracer().info("%s - %s" % (name, message))


def debug(name=__name__, message=None, log=True):
    """
    same as info but debug
    """
    if log:
        logging.getLogger(name).debug(message)

    if orca.get_injectable('enable_trace_log'):
        get_tracer().debug("%s - %s" % (name, message))


def warn(name=__name__, message=None, log=True):
    """
    same as info but warn
    """
    if log:
        logging.getLogger(name).warn(message)

    if orca.get_injectable('enable_trace_log'):
        get_tracer().warn("%s - %s" % (name, message))


def error(name=__name__, message=None, log=True):
    """
    same as info but warn
    """
    if log:
        logging.getLogger(name).error(message)

    if orca.get_injectable('enable_trace_log'):
        get_tracer().error("%s - %s" % (name, message))


def print_summary(label, df, describe=False, value_counts=False):
    """
    Print summary

    Parameters
    ----------
    label: str
        tracer name
    df: pandas.DataFrame
        traced dataframe
    describe: boolean
        print describe?
    value_counts: boolean
        print value counts?

    Returns
    -------
    Nothing
    """

    if not (value_counts or describe):
        error(__name__, "print_summary neither value_counts nor describe")

    if value_counts:
        print "\n%s choices value counts:\n%s\n" % (label, df.value_counts())

    if describe:
        print "\n%s choices summary:\n%s\n" % (label, df.describe())


def register_households(df, trace_hh_id):
    """
    Register with orca households for tracing

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    trace_hh_id: int
        household ID to trace

    Returns
    -------
    Nothing
    """
    tracer = get_tracer()

    if trace_hh_id is None:
        error(message="register_households called with null trace_hh_id")
        return

    info(message="tracing household id %s in %s households" % (trace_hh_id, len(df.index)))

    if trace_hh_id not in df.index:
        warn(message="trace_hh_id %s not in dataframe")

    # inject persons_index name of person dataframe index
    if df.index.name is None:
        df.index.names = ['household_id']
        warn(message="households table index had no name. renamed index '%s'" % df.index.name)
    orca.add_injectable("hh_index_name", df.index.name)

    debug(message="register_households injected hh_index_name '%s'" % df.index.name)


def register_persons(df, trace_hh_id):
    """
    Register with orca persons for tracing

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    trace_hh_id: int
        household ID to trace

    Returns
    -------
    Nothing
    """
    tracer = get_tracer()

    if trace_hh_id is None:
        warn(message="register_persons called with null trace_hh_id")
        return

    # inject persons_index name of person dataframe index
    if df.index.name is None:
        df.index.names = ['person_id']
        warn(message="persons table index had no name. renamed index '%s'" % df.index.name)
    orca.add_injectable("persons_index_name", df.index.name)

    debug(message="register_persons injected persons_index_name '%s'" % df.index.name)

    # inject list of person_ids in household we are tracing
    # this allows us to slice by person_id without requiring presence of household_id column
    traced_persons_df = df[df['household_id'] == trace_hh_id]
    trace_person_ids = traced_persons_df.index.tolist()
    if len(trace_person_ids) == 0:
        warn(message="register_persons: trace_hh_id %s not found." % trace_hh_id)

    orca.add_injectable("trace_person_ids", trace_person_ids)
    debug(message="register_persons injected trace_person_ids %s" % trace_person_ids)

    info(message="tracing person_ids %s in %s persons" % (trace_person_ids, len(df.index)))


def write_df_csv(df, file_path, index_label=None, columns=None, column_labels=None, transpose=True):

    mode = 'a' if os.path.isfile(file_path) else 'w'

    if columns:
        df = df[columns]

    if not transpose:
        df.to_csv(file_path, mmode="a", index=True, header=True)
        return

    df_t = df.transpose()
    if df.index.name is not None:
        df_t.index.name = df.index.name
    elif index_label:
        df_t.index.name = index_label

    with open(file_path, mode=mode) as f:
        if column_labels is None:
            column_labels = [None, None]
        if column_labels[0] is None:
            column_labels[0] = 'label'
        if column_labels[1] is None:
            column_labels[1] = 'value'

        if len(df_t.columns) == len(column_labels) - 1:
            column_label_row = ','.join(column_labels)
        else:
            column_label_row = \
                column_labels[0] + ',' \
                + ','.join([column_labels[1] + '_' + str(i+1) for i in range(len(df_t.columns))])

        if mode == 'a':
            column_label_row = '# ' + column_label_row
        f.write(column_label_row + '\n')
    df_t.to_csv(file_path, mode='a', index=True, header=True)


def write_series_csv(series, file_path, index_label=None, columns=None, column_labels=None):

    if isinstance(columns, str):
        series = series.rename(columns)
    elif isinstance(columns, list):
        if columns[0]:
            series.index.name = columns[0]
        series = series.rename(columns[1])
    if index_label and series.index.name is None:
        series.index.name = index_label
    series.to_csv(file_path, mode='a', index=True, header=True)


def trace_od_idx():

    od = orca.get_injectable('trace_od')

    o = od[0] - 1
    d = od[1] - 1
    return o, d


def trace_array(name, a, array_name):

    shape = a.shape

    o, d = orca.get_injectable('trace_od')
    o_idx, d_idx = trace_od_idx()

    if len(shape) == 1:
        info(name=name, message="%s[dest_taz=%s] = %s" % (array_name, d, a[d_idx]))
    elif len(shape) == 2:
        info(name=name, message="%s[%s, %s] = %s" % (array_name, o, d, a[o_idx, d_idx]))
    else:
        warn(name=name, message="trace_array doesn't grok %s shape %s" % (array_name, shape, ))


def write_array(a, file_name, fmt=None):

    info(message="dumping %s array to %s" % (a.shape, file_name))
    file_path = log_file_path('%s.%s' % (file_name, CSV_FILE_TYPE))
    np.savetxt(file_path, a, delimiter=',', fmt=fmt)


def write_csv(df, file_name, index_label=None, columns=None, column_labels=None, transpose=True):
    """
    Print write_csv

    Parameters
    ----------
    df: pandas.DataFrame or pandas.Series
        traced dataframe
    file_name: str
        output file name
    index_label: str
        index name
    columns: list
        columns to write
    transpose: bool
        whether to transpose dataframe (ignored for series)
    Returns
    -------
    Nothing
    """
    tracer = get_tracer()

    if isinstance(df, pd.Series):
        # file_name = "%s.series" % file_name
        debug(message="dumping %s element series to %s" % (len(df.index), file_name))
    else:
        # file_name = "%s.df" % file_name
        debug(message="dumping %s dataframe to %s" % (df.shape, file_name))

    file_path = log_file_path('%s.%s' % (file_name, CSV_FILE_TYPE))

    if os.path.isfile(file_path):
        error(message="write_csv file exists %s %s" % (type(df).__name__, file_name))

    if isinstance(df, pd.DataFrame):
        write_df_csv(df, file_path, index_label, columns, column_labels, transpose=transpose)
    elif isinstance(df, pd.Series):
        write_series_csv(df, file_path, index_label, columns, column_labels)
    else:
        tracer.error("write_df_csv object '%s' of unexpected type: %s" % (file_name, type(df)))


def slice_ids(df, ids, column=None, label=None):
    """
    slice a dataframe to select only records with the specified ids

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    ids: int or list of ints
        slice ids
    column: str
        column to slice (slice using index if None)

    Returns
    -------
    df: pandas.DataFrame
        sliced dataframe
    """

    if not isinstance(ids, (list, tuple)):
        ids = [ids]
    try:
        if column is None:
            df = df.loc[ids]
        else:
            df = df[df[column].isin(ids)]
    except KeyError:
        df = df[0:0]
    return df


def canonical_slicer(index_name):
    """
    return a canonical column name and targets (hh id or person ids) to
    annotate a dataframe with trace targets in a manner grokable by slice_canonically method

    Parameters
    ----------
    index_name: str
        name of column or index to use for slicing

    Returns
    -------
        name of column to use
        target hh_id or person_ids
    """
    if index_name == 'PERID' or index_name == orca.get_injectable('persons_index_name'):
        column_name = 'person_id'
    elif index_name == 'HHID' or index_name == orca.get_injectable('hh_index_name'):
        column_name = 'hh_id'
    elif index_name == 'tour_id':
        column_name = 'person_id'
    else:
        get_tracer().error("canonical_slicer undefined for index %s" % (index_name,))
        column_name = ''

    if column_name == 'person_id':
        targets = orca.get_injectable('trace_person_ids')
    elif column_name == 'hh_id':
        targets = [orca.get_injectable('trace_hh_id')]
    else:
        targets = []

    return column_name, targets


def slice_canonically(df, slicer, label):
    """
    Slice dataframe by traced household or person id dataframe and write to CSV

    Parameters
    ----------
    df: pandas.DataFrame
        dataframe to slice
    slicer: str
        name of column or index to use for slicing
    label: str
        tracer name - only used to report bad slicer

    Returns
    -------
    sliced subset of dataframe
    """

    tracer = get_tracer()

    if slicer is None:
        slicer = df.index.name

    if slicer == 'PERID' or slicer == orca.get_injectable('persons_index_name'):
        df = slice_ids(df, orca.get_injectable('trace_person_ids'))
    elif slicer == 'HHID' or slicer == orca.get_injectable('hh_index_name'):
        df = slice_ids(df, orca.get_injectable('trace_hh_id'))
    elif slicer == 'person_id':
        df = slice_ids(df, orca.get_injectable('trace_person_ids'), column='person_id')
    elif slicer == 'hh_id':
        df = slice_ids(df, orca.get_injectable('trace_hh_id'), column='hh_id')
    elif slicer == 'tour_id':
        df = slice_ids(df, orca.get_injectable('trace_person_ids'), column='person_id')
    elif slicer == 'taz' or slicer == 'ZONE':
        df = slice_ids(df, orca.get_injectable('trace_od'))
    elif slicer == 'NONE':
        pass
    else:
        get_tracer().error("slice_canonically: bad slicer '%s' for %s " % (slicer, label))
        print df.head(3)
        df = df[0:0]

    # tracer.debug("slice_canonically slicing %s by %s got %s" % (label, slicer, len(df.index)))

    return df


def trace_df(df, label, slicer=None, columns=None,
             index_label=None, column_labels=None, transpose=True, warn=True):
    """
    Slice dataframe by traced household or person id dataframe and write to CSV

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    label: str
        tracer name
    slicer: Object
        slicer for subsetting
    columns: list
        columns to write
    index_label: str
        index name
    column_labels: [str, str]
        labels for columns in csv
    transpose: boolean
        whether to transpose file for legibility
    warn: boolean
        write warnings

    Returns
    -------
    Nothing
    """
    tracer = get_tracer()

    df = slice_canonically(df, slicer, label)

    if len(df.index) > 0:
        write_csv(df, file_name=label, index_label=(index_label or slicer), columns=columns,
                  column_labels=column_labels, transpose=transpose)
    elif warn:
        tracer.warn("%s: no rows with id" % (label, ))


def trace_choosers(df, label):
    """
    Trace choosers

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    trace_df(df, '%s.choosers' % label, warn=False)


def trace_utilities(df, label):
    """
    Trace utilities

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    trace_df(df, '%s.utilities' % label, column_labels=['alternative', 'utility'], warn=False)


def trace_probs(df, label):
    """
    Trace probabilities

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    trace_df(df, '%s.probs' % label, column_labels=['alternative', 'probability'], warn=False)


def trace_choices(df, label, columns=None):
    """
    Trace choices

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    trace_df(df, '%s.choices' % label, columns=columns, warn=False)


def trace_model_design(df, label):
    """
    Trace model design

    Parameters
    ----------
    df: pandas.DataFrame
        traced dataframe
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    trace_df(df, '%s.model_design' % label, column_labels=['expression', None], warn=False)


def trace_interaction_model_design(model_design, choosers, label):
    """
    Trace model design for interaction_simulate

    Parameters
    ----------
    model_design: pandas.DataFrame
        traced model_design dataframe
    choosers: pandas.DataFrame
        interaction_simulate choosers
        (needed to filter the model_design dataframe by traced hh or person id)
    label: str
        tracer name

    Returns
    -------
    Nothing
    """

    label = '%s.model_design' % label

    # column name to use for chooser id (hh or person) added to model_design dataframe
    slicer_column_name, targets = canonical_slicer(choosers.index.name)

    # we can deduce the sample_size from the relative size of model_design and choosers
    # (model design rows are repeated once for each alternative)
    sample_size = len(model_design.index) / len(choosers.index)

    # we need to repeat each value sample_size times
    slicer_column_values = np.repeat(choosers.index.values, sample_size)
    model_design[slicer_column_name] = slicer_column_values
    model_design_index_name = model_design.index.name

    if model_design_index_name is None:
        debug(message="model_design.index.name for %s is None" % label)
        model_design_index_name = 'index'
        model_design.index.rename(model_design_index_name, inplace=True)

    # pre-slice for runtime efficiency
    df = slice_canonically(model_design, slicer_column_name, label)

    if len(df.index) == 0:
        return

    # write out the raw dataframe
    file_path = log_file_path('%s.raw.csv' % label)
    df.to_csv(file_path, mmode="a", index=True, header=True)

    # if there are multiple targets, we want them in seperate tables for readability
    for target in targets:
        df_target = slice_ids(df, target, column=slicer_column_name)

        if len(df_target.index) == 0:
            continue

        # we want the transposed columns in predictable order
        df_target.sort_index(inplace=True)

        # remove the slicer (person_id or hh_id) column?
        del df_target[slicer_column_name]

        target_label = '%s.%s.%s' % (label, slicer_column_name, target)
        trace_df(df_target, target_label,
                 slicer="NONE",
                 transpose=True,
                 column_labels=['expression', None],
                 warn=False)


def trace_cdap_hh_utils(hh_utils, label):
    """
    Trace CDAP household utilities

    Parameters
    ----------
    hh_utils: pandas.DataFrame
        hh_utils
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    # hh_util : dict of pandas.Series
    #     Keys will be household IDs and values will be Series
    #     mapping alternative choices to their utility.
    hh_id = orca.get_injectable('trace_hh_id')
    s = hh_id and hh_utils.get(hh_id, None)
    if s is not None:
        trace_df(s, label, slicer='NONE', columns=['choice', 'utility'], warn=False)


def trace_cdap_ind_utils(ind_utils, label):
    """
    Trace CDAP ind utilities

    Parameters
    ----------
    ind_utils: pandas.DataFrame
        ind_utils
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    trace_df(ind_utils, label, slicer='PERID', warn=False)


def trace_nan_values(df, label):
    """
    Trace NaN values

    Parameters
    ----------
    df: pandas.DataFrame
        data frame
    label: str
        tracer name

    Returns
    -------
    Nothing
    """
    df = slice_ids(df, orca.get_injectable('trace_person_ids'))
    if np.isnan(df).any():
        get_tracer().warn("%s NaN values in %s" % (np.isnan(df).sum(), label))
        write_df_csv(df, "%s.nan" % label)
