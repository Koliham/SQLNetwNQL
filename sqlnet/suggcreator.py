import json
from .lib.dbengine import DBEngine
import re
import numpy as np
import pandas as pd

from models.nql import NQL

def create_suggestions(model,txtstring,tableinfo):
    suggestions = {}
    engine = DBEngine("data/test.db")
    tid = tableinfo["id"]
    q_seq = txtstring.split(" ")
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
    gt_sel_seq = 0

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

def suggestion_worker(model, batch_size, sql_data, table_data, db_path):
    # Mehmet

    cols = ["table", "question", "ex_correct", "correct_index", "correct_any", "agg_wrong", "sel_wrong", "conds_wrong"]
    df = pd.DataFrame(columns=cols)

    # -----Mehmet

    engine = DBEngine(db_path)

    model.eval()
    perm = list(range(len(sql_data)))
    in_acc_num = 0.0
    tot_acc_num = 0.0
    acc_of_log = 0.0
    st = 0
    while st < len(sql_data):
        ed = st + batch_size if st + batch_size < len(perm) else len(perm)
        q_seq, col_seq, col_num, ans_seq, query_seq, gt_cond_seq, raw_data = \
            to_batch_seq(sql_data, table_data, perm, st, ed, ret_vis_data=True)
        raw_q_seq = [x[0] for x in raw_data]
        raw_col_seq = [x[1] for x in raw_data]
        gt_where_seq = model.generate_gt_where_seq(q_seq, col_seq, query_seq)
        query_gt, table_ids = to_batch_query(sql_data, perm, st, ed)
        gt_sel_seq = [x[1] for x in ans_seq]
        score = model.forward(q_seq, col_seq, col_num,
                              (True, True, True), gt_sel=gt_sel_seq)
        pred_queries, all_preds = model.gen_query(score, q_seq, col_seq,
                                                  raw_q_seq, raw_col_seq, (True, True, True))

        for idx, (sql_gt, sql_pred, tid) in enumerate(
                zip(query_gt, pred_queries, table_ids)):
            ret_gt = engine.execute(tid,
                                    sql_gt['sel'], sql_gt['agg'], sql_gt['conds'])
            try:
                ret_pred = engine.execute(tid,
                                          sql_pred['sel'], sql_pred['agg'], sql_pred['conds'])
            except:
                ret_pred = None
            tot_acc_num += (ret_gt == ret_pred)

            # Mehmet
            line = {}
            line["agg_wrong"] = 1
            line["sel_wrong"] = 1
            line["conds_wrong"] = 1

            # find , if the correct is amont the theoretical results
            top1correct = 1 if ret_gt == ret_pred else 0
            if top1correct:
                line["correct_index"] = 1
                line["correct_any"] = 1
                line["agg_wrong"] = 0
                line["sel_wrong"] = 0
                line["conds_wrong"] = 0
                in_acc_num += 1

            else:
                line["correct_index"] = -1
                line["correct_any"] = 0
                predlist = all_preds[idx]
                for posi, pdict in enumerate(predlist):
                    try:
                        predvariant = engine.execute(tid,
                                                     pdict['sel'], pdict['agg'], pdict['conds'])
                    except:
                        predvariant = None
                    if ret_gt == predvariant:
                        line["correct_index"] = posi + 1
                        line["correct_any"] = 1
                        line["agg_wrong"] = 0
                        line["sel_wrong"] = 0
                        line["conds_wrong"] = 0
                        in_acc_num += 1
                        break
                    else:
                        if pdict["sel"] == sql_gt["sel"]: line["sel_wrong"] = 0
                        if pdict["agg"] == sql_gt["agg"]: line["agg_wrong"] = 0
                        if pdict["conds"] == sql_gt["conds"]: line["conds_wrong"] = 0

            line["table"] = table_ids[idx]
            line["question"] = raw_q_seq[idx].encode("utf-8")
            line["ex_correct"] = top1correct
            df = df.append(line, ignore_index=True)
            # ---Mehmet

        st = ed
    # TODO: uncomment to write result
    # df.to_csv("nqlresult.csv",sep=";",index=False)
    print("acc before:", tot_acc_num / len(sql_data))
    print("acc incrwased: ", in_acc_num / len(sql_data))
    return tot_acc_num / len(sql_data)

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