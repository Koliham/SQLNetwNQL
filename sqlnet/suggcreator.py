import json
from .lib.dbengine import DBEngine
import re
import numpy as np
import pandas as pd
import random

from models.nql import NQL

def create_suggestions(model,txtstring,tableinfo):
    suggestions = {}
    engine = DBEngine("data/test.db")
    tid = tableinfo["id"]
    q_seq = txtstring.split(" ")
    # q_seq = re.findall(r"[ ']",txtstring)
    if "header_tok" in tableinfo.keys():
        col_seq = tableinfo["header_tok"]
    else:
        col_seq = []
        cols_raw = tableinfo["header"]
        for wort in cols_raw:
            wlist = wort.split(" ")
            col_seq.append(wlist)
    col_num = len(tableinfo["header"])
    raw_q_seq = txtstring
    raw_col_seq = tableinfo["header"]
    gt_sel_seq = random.randint(0,col_num-1)

    #convert to 2-array
    q_seq = [q_seq,q_seq]
    col_seq = [col_seq,col_seq]
    col_num = [col_num,col_num]
    raw_q_seq = [raw_q_seq,raw_q_seq]
    raw_col_seq = [raw_col_seq,raw_col_seq]
    gt_sel_seq = [gt_sel_seq,gt_sel_seq]


    score = model.forward(q_seq, col_seq, col_num,
                          (True, True, True), gt_sel=gt_sel_seq)

    pred_queries, all_preds = model.gen_query(score, q_seq, col_seq,
                                              raw_q_seq, raw_col_seq, (True, True, True))
    pred_queries = pred_queries[0]
    all_preds = all_preds[0]
    num_results = 10
    random.shuffle(all_preds)
    all_preds = all_preds[0:num_results-1]

    all_preds = [pred_queries] + all_preds

    for i in range(len(all_preds)):
        nqlo = NQL.fromwikisql(all_preds[i], tableinfo)
        try:
            ret_pred = engine.execute(tid,
                                      all_preds[i]['sel'], all_preds[i]['agg'], all_preds[i]['conds'])
        except:
            ret_pred = None
        suggestions[nqlo.inl()] = str(ret_pred)
    return suggestions


def parse_nql(txtstring,tableinfo):
    engine = DBEngine("data/test.db")
    tid = tableinfo["id"]
    nqlo = NQL.frominl(txtstring)
    nqlo.wikisqltableschema = tableinfo
    nqldict = nqlo.wikisqldict()
    try:
        ret_pred = engine.execute(tid,
                                  nqldict['sel'], nqldict['agg'], nqldict['conds'])
    except:
        ret_pred = None
    return ret_pred

def to_batch_seq(sql_data, table_data, idxes, st, ed, ret_vis_data=False):
    q_seq = []
    col_seq = []
    col_num = []
    ans_seq = []
    query_seq = []
    gt_cond_seq = []
    vis_seq = []
    for i in range(st, ed):
        sql = sql_data[idxes[i]]
        q_seq.append(sql['question_tok'])
        col_seq.append(table_data[sql['table_id']]['header_tok'])
        col_num.append(len(table_data[sql['table_id']]['header']))
        ans_seq.append((sql['sql']['agg'],
            sql['sql']['sel'],
            len(sql['sql']['conds']),
            tuple(x[0] for x in sql['sql']['conds']),
            tuple(x[1] for x in sql['sql']['conds'])))
        query_seq.append(sql['query_tok'])
        gt_cond_seq.append(sql['sql']['conds'])
        vis_seq.append((sql['question'],
            table_data[sql['table_id']]['header'], sql['query']))
    if ret_vis_data:
        return q_seq, col_seq, col_num, ans_seq, query_seq, gt_cond_seq, vis_seq
    else:
        return q_seq, col_seq, col_num, ans_seq, query_seq, gt_cond_seq

def to_batch_query(sql_data, idxes, st, ed):
    query_gt = []
    table_ids = []
    for i in range(st, ed):
        query_gt.append(sql_data[idxes[i]]['sql'])
        table_ids.append(sql_data[idxes[i]]['table_id'])
    return query_gt, table_ids