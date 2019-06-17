import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np
from .modules.word_embedding import WordEmbedding
from .modules.aggregator_predict import AggPredictor
from .modules.selection_predict import SelPredictor
from .modules.sqlnet_condition_predict import SQLNetCondPredictor


class SQLNet(nn.Module):
    def __init__(self, word_emb, N_word, N_h=100, N_depth=2,
            gpu=False, use_ca=True, trainable_emb=False):
        super(SQLNet, self).__init__()
        self.use_ca = use_ca
        self.trainable_emb = trainable_emb

        self.gpu = gpu
        self.N_h = N_h
        self.N_depth = N_depth

        self.max_col_num = 45
        self.max_tok_num = 200
        self.SQL_TOK = ['<UNK>', '<END>', 'WHERE', 'AND',
                'EQL', 'GT', 'LT', '<BEG>']
        self.COND_OPS = ['EQL', 'GT', 'LT']

        #Word embedding
        if trainable_emb:
            self.agg_embed_layer = WordEmbedding(word_emb, N_word, gpu,
                    self.SQL_TOK, our_model=True, trainable=trainable_emb)
            self.sel_embed_layer = WordEmbedding(word_emb, N_word, gpu,
                    self.SQL_TOK, our_model=True, trainable=trainable_emb)
            self.cond_embed_layer = WordEmbedding(word_emb, N_word, gpu,
                    self.SQL_TOK, our_model=True, trainable=trainable_emb)
        else:
            self.embed_layer = WordEmbedding(word_emb, N_word, gpu,
                    self.SQL_TOK, our_model=True, trainable=trainable_emb)
        
        #Predict aggregator
        self.agg_pred = AggPredictor(N_word, N_h, N_depth, use_ca=use_ca)

        #Predict selected column
        self.sel_pred = SelPredictor(N_word, N_h, N_depth,
                self.max_tok_num, use_ca=use_ca)

        #Predict number of cond
        self.cond_pred = SQLNetCondPredictor(N_word, N_h, N_depth,
                self.max_col_num, self.max_tok_num, use_ca, gpu)


        self.CE = nn.CrossEntropyLoss()
        self.softmax = nn.Softmax()
        self.log_softmax = nn.LogSoftmax()
        self.bce_logit = nn.BCEWithLogitsLoss()
        if gpu:
            self.cuda()


    def generate_gt_where_seq(self, q, col, query):
        ret_seq = []
        for cur_q, cur_col, cur_query in zip(q, col, query):
            cur_values = []
            st = cur_query.index('WHERE')+1 if \
                    'WHERE' in cur_query else len(cur_query)
            all_toks = ['<BEG>'] + cur_q + ['<END>']
            while st < len(cur_query):
                ed = len(cur_query) if 'AND' not in cur_query[st:]\
                        else cur_query[st:].index('AND') + st
                if 'EQL' in cur_query[st:ed]:
                    op = cur_query[st:ed].index('EQL') + st
                elif 'GT' in cur_query[st:ed]:
                    op = cur_query[st:ed].index('GT') + st
                elif 'LT' in cur_query[st:ed]:
                    op = cur_query[st:ed].index('LT') + st
                else:
                    raise RuntimeError("No operator in it!")
                this_str = ['<BEG>'] + cur_query[op+1:ed] + ['<END>']
                cur_seq = [all_toks.index(s) if s in all_toks \
                        else 0 for s in this_str]
                cur_values.append(cur_seq)
                st = ed+1
            ret_seq.append(cur_values)
        return ret_seq


    def forward(self, q, col, col_num, pred_entry,
            gt_where = None, gt_cond=None, reinforce=False, gt_sel=None):
        B = len(q)
        pred_agg, pred_sel, pred_cond = pred_entry

        agg_score = None
        sel_score = None
        cond_score = None

        #Predict aggregator
        if self.trainable_emb:
            if pred_agg:
                x_emb_var, x_len = self.agg_embed_layer.gen_x_batch(q, col)
                col_inp_var, col_name_len, col_len = \
                        self.agg_embed_layer.gen_col_batch(col)
                max_x_len = max(x_len)
                agg_score = self.agg_pred(x_emb_var, x_len, col_inp_var,
                        col_name_len, col_len, col_num, gt_sel=gt_sel)

            if pred_sel:
                x_emb_var, x_len = self.sel_embed_layer.gen_x_batch(q, col)
                col_inp_var, col_name_len, col_len = \
                        self.sel_embed_layer.gen_col_batch(col)
                max_x_len = max(x_len)
                sel_score = self.sel_pred(x_emb_var, x_len, col_inp_var,
                        col_name_len, col_len, col_num)

            if pred_cond:
                x_emb_var, x_len = self.cond_embed_layer.gen_x_batch(q, col)
                col_inp_var, col_name_len, col_len = \
                        self.cond_embed_layer.gen_col_batch(col)
                max_x_len = max(x_len)
                cond_score = self.cond_pred(x_emb_var, x_len, col_inp_var,
                        col_name_len, col_len, col_num,
                        gt_where, gt_cond, reinforce=reinforce)
        else:
            x_emb_var, x_len = self.embed_layer.gen_x_batch(q, col)
            col_inp_var, col_name_len, col_len = \
                    self.embed_layer.gen_col_batch(col)
            max_x_len = max(x_len)
            if pred_agg:
                agg_score = self.agg_pred(x_emb_var, x_len, col_inp_var,
                        col_name_len, col_len, col_num, gt_sel=gt_sel)

            if pred_sel:
                sel_score = self.sel_pred(x_emb_var, x_len, col_inp_var,
                        col_name_len, col_len, col_num)

            if pred_cond:
                cond_score = self.cond_pred(x_emb_var, x_len, col_inp_var,
                        col_name_len, col_len, col_num,
                        gt_where, gt_cond, reinforce=reinforce)

        return (agg_score, sel_score, cond_score)

    def loss(self, score, truth_num, pred_entry, gt_where):
        pred_agg, pred_sel, pred_cond = pred_entry
        agg_score, sel_score, cond_score = score

        loss = 0
        if pred_agg:
            agg_truth = [x[0] for x in truth_num]
            data = torch.from_numpy(np.array(agg_truth))
            if self.gpu:
                agg_truth_var = Variable(data.cuda())
            else:
                agg_truth_var = Variable(data)

            loss += self.CE(agg_score, agg_truth_var)

        if pred_sel:
            sel_truth = [x[1] for x in truth_num]
            data = torch.from_numpy(np.array(sel_truth))
            if self.gpu:
                sel_truth_var = Variable(data.cuda())
            else:
                sel_truth_var = Variable(data)

            loss += self.CE(sel_score, sel_truth_var)

        if pred_cond:
            B = len(truth_num)
            cond_num_score, cond_col_score,\
                    cond_op_score, cond_str_score = cond_score
            #Evaluate the number of conditions
            cond_num_truth = [x[2] for x in truth_num]
            data = torch.from_numpy(np.array(cond_num_truth))
            if self.gpu:
                cond_num_truth_var = Variable(data.cuda())
            else:
                cond_num_truth_var = Variable(data)
            loss += self.CE(cond_num_score, cond_num_truth_var)

            #Evaluate the columns of conditions
            T = len(cond_col_score[0])
            truth_prob = np.zeros((B, T), dtype=np.float32)
            for b in range(B):
                if len(truth_num[b][3]) > 0:
                    truth_prob[b][list(truth_num[b][3])] = 1
            data = torch.from_numpy(truth_prob)
            if self.gpu:
                cond_col_truth_var = Variable(data.cuda())
            else:
                cond_col_truth_var = Variable(data)

            sigm = nn.Sigmoid()
            cond_col_prob = sigm(cond_col_score)
            bce_loss = -torch.mean( 3*(cond_col_truth_var * \
                    torch.log(cond_col_prob+1e-10)) + \
                    (1-cond_col_truth_var) * torch.log(1-cond_col_prob+1e-10) )
            loss += bce_loss

            #Evaluate the operator of conditions
            for b in range(len(truth_num)):
                if len(truth_num[b][4]) == 0:
                    continue
                data = torch.from_numpy(np.array(truth_num[b][4]))
                if self.gpu:
                    cond_op_truth_var = Variable(data.cuda())
                else:
                    cond_op_truth_var = Variable(data)
                cond_op_pred = cond_op_score[b, :len(truth_num[b][4])]
                loss += (self.CE(cond_op_pred, cond_op_truth_var) \
                        / len(truth_num))

            #Evaluate the strings of conditions
            for b in range(len(gt_where)):
                for idx in range(len(gt_where[b])):
                    cond_str_truth = gt_where[b][idx]
                    if len(cond_str_truth) == 1:
                        continue
                    data = torch.from_numpy(np.array(cond_str_truth[1:]))
                    if self.gpu:
                        cond_str_truth_var = Variable(data.cuda())
                    else:
                        cond_str_truth_var = Variable(data)
                    str_end = len(cond_str_truth)-1
                    cond_str_pred = cond_str_score[b, idx, :str_end]
                    loss += (self.CE(cond_str_pred, cond_str_truth_var) \
                            / (len(gt_where) * len(gt_where[b])))

        return loss

    def check_acc(self, vis_info, pred_queries, gt_queries, pred_entry):
        def pretty_print(vis_data):
            print('question:', vis_data[0])
            print('headers: (%s)'%(' || '.join(vis_data[1])))
            print('query:', vis_data[2])

        def gen_cond_str(conds, header):
            if len(conds) == 0:
                return 'None'
            cond_str = []
            for cond in conds:
                cond_str.append(header[cond[0]] + ' ' +
                    self.COND_OPS[cond[1]] + ' ' + str(cond[2]).lower())
            return 'WHERE ' + ' AND '.join(cond_str)

        pred_agg, pred_sel, pred_cond = pred_entry

        B = len(gt_queries)

        tot_err = agg_err = sel_err = cond_err = 0.0
        cond_num_err = cond_col_err = cond_op_err = cond_val_err = 0.0
        agg_ops = ['None', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
        for b, (pred_qry, gt_qry) in enumerate(zip(pred_queries, gt_queries)):
            good = True
            if pred_agg:
                agg_pred = pred_qry['agg']
                agg_gt = gt_qry['agg']
                if agg_pred != agg_gt:
                    agg_err += 1
                    good = False

            if pred_sel:
                sel_pred = pred_qry['sel']
                sel_gt = gt_qry['sel']
                if sel_pred != sel_gt:
                    sel_err += 1
                    good = False

            if pred_cond:
                cond_pred = pred_qry['conds']
                cond_gt = gt_qry['conds']
                flag = True
                if len(cond_pred) != len(cond_gt):
                    flag = False
                    cond_num_err += 1

                if flag and set(x[0] for x in cond_pred) != \
                        set(x[0] for x in cond_gt):
                    flag = False
                    cond_col_err += 1

                for idx in range(len(cond_pred)):
                    if not flag:
                        break
                    gt_idx = tuple(
                            x[0] for x in cond_gt).index(cond_pred[idx][0])
                    if flag and cond_gt[gt_idx][1] != cond_pred[idx][1]:
                        flag = False
                        cond_op_err += 1

                for idx in range(len(cond_pred)):
                    if not flag:
                        break
                    gt_idx = tuple(
                            x[0] for x in cond_gt).index(cond_pred[idx][0])
                    if flag and str(cond_gt[gt_idx][2]).lower() != \
                            str(cond_pred[idx][2]).lower():
                        flag = False
                        cond_val_err += 1

                if not flag:
                    cond_err += 1
                    good = False

            if not good:
                tot_err += 1

        return np.array((agg_err, sel_err, cond_err)), tot_err


    def gen_query(self, score, q, col, raw_q, raw_col,
            pred_entry, reinforce=False, verbose=False):

        def merge_tokens_v2(tok_list):
            if len(tok_list)==1:
                return tok_list[0]
            else:
                return " ".join(tok_list)


        def merge_tokens(tok_list, raw_tok_str):
            tok_str = raw_tok_str.lower()
            alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789$('
            special = {'-LRB-':'(',
                    '-RRB-':')',
                    '-LSB-':'[',
                    '-RSB-':']',
                    '``':'"',
                    '\'\'':'"',
                    '--':'\u2013'}
            ret = ''
            double_quote_appear = 0
            for raw_tok in tok_list:
                if not raw_tok:
                    continue
                tok = special.get(raw_tok, raw_tok)
                if tok == '"':
                    double_quote_appear = 1 - double_quote_appear

                if len(ret) == 0:
                    pass
                elif len(ret) > 0 and ret + ' ' + tok in tok_str:
                    ret = ret + ' '
                elif len(ret) > 0 and ret + tok in tok_str:
                    pass
                elif tok == '"':
                    if double_quote_appear:
                        ret = ret + ' '
                elif tok[0] not in alphabet:
                    pass
                elif (ret[-1] not in ['(', '/', '\u2013', '#', '$', '&']) \
                        and (ret[-1] != '"' or not double_quote_appear):
                    ret = ret + ' '
                ret = ret + tok
            return ret.strip()

        pred_agg, pred_sel, pred_cond = pred_entry
        agg_score, sel_score, cond_score = score

        ret_queries = []
        ret_querylist = [] # Mehmet
        if pred_agg:
            B = len(agg_score)
        elif pred_sel:
            B = len(sel_score)
        elif pred_cond:
            B = len(cond_score[0])
        for b in range(B):
            cur_query = {}
            cur_arglist = {} # Mehmet
            if pred_agg:
                cur_query['agg'] = np.argmax(agg_score[b].data.cpu().numpy())

                # also get the second highest arg, if it is > 0
                args_temp = np.argsort(-agg_score[b].data.cpu().numpy())[0:2]
                if agg_score[b].data.cpu().numpy()[0] > 0: # if even the first one should be < 0
                    cur_arglist['agg'] = [x for x in args_temp if agg_score[b].data.cpu().numpy()[x] > 0]
                else:
                    cur_arglist['agg'] = [cur_query['agg']]
                # ----
            if pred_sel:
                cur_query['sel'] = np.argmax(sel_score[b].data.cpu().numpy())
                cur_arglist['sel'] = np.argsort(-sel_score[b].data.cpu().numpy())[0:2] # Mehmet
            if pred_cond:
                cur_query['conds'] = []

                cur_arglist['conds'] = [] # Mehmet
                cur_arglist["nums"] = [] # Mehmet
                cur_arglist["texte"] = [] # Mehmet

                cond_num_score,cond_col_score,cond_op_score,cond_str_score =\
                        [x.data.cpu().numpy() for x in cond_score]
                cond_num = np.argmax(cond_num_score[b])

                #get the two possible number of cols
                num_possible = np.argsort(-cond_num_score[b])[0:2]
                if num_possible[0]> 0:
                    cur_arglist["nums"] = [x for x in num_possible if cond_num_score[b][x] > 0]
                else:
                    cur_arglist["nums"] = [cond_num]
                # ----

                all_toks = ['<BEG>'] + q[b] + ['<END>']
                max_idxes = np.argsort(-cond_col_score[b]) # [:cond_num] removed

                #copy pasted the code from iteration ofver the range of cond_num
                # idea: For each possible number of columns create a cond block.
                # each condblock has 4 elements. Each element is a list.
                # in each element, the cond with the respective text id (1,2,3,4) is added
                textstringnum = 4
                selvariation = 2
                condblock = [None]*len(cur_arglist["nums"])
                for bid, numcols in enumerate(cur_arglist["nums"]):
                    condblock[bid] = []
                    for i in range(textstringnum*selvariation):
                        condblock[bid].append([]) # 4 time, each list is for one str alt

                    for idx in range(numcols):
                        cur_cond = []
                        cur_cond.append(max_idxes[idx])
                        cur_cond.append(np.argmax(cond_op_score[b][idx])) # no change for simplicity:

                        #version 2 of cur_cond
                        cur_cond_v2 = []
                        cur_cond_v2.append(max_idxes[idx+1])
                        cur_cond_v2.append(np.argmax(cond_op_score[b][idx]))  # no change for simplicity:

                        # idea: create 4 (=textstringnum) versions:
                        strteile = []
                        strteile.append([]) # [0] one standard, where the argmax is taken
                        strteile.append([]) # [1] is for argmax first str, then 2nd. candidate
                        strteile.append([]) # [2] 2nd. candidate, then argmax
                        strteile.append([]) # [3] 2nd. candidate, then 2nd. candidate
                        # after that, the remaining strings are the first candidate

                        secondfill = True # set to False, when the alt already has <END>
                        for ii, str_score in enumerate(cond_str_score[b][idx]):
                            str_tok = np.argmax(str_score[:len(all_toks)])
                            str_tok_alt2 = np.argsort(-str_score[:len(all_toks)])[1]
                            str_val = all_toks[str_tok]
                            str_val_alt2 = all_toks[str_tok_alt2]
                            if str_val == '<END>':
                                break
                            if str_val_alt2=='<END>':
                                secondfill=False
                            if ii==0:
                                strteile[0].append(str_val)
                                strteile[1].append(str_val)
                                if str_val_alt2 != '<END>' and str_val_alt2 != "": strteile[2].append(str_val_alt2)
                                if str_val_alt2 != '<END>' and str_val_alt2 != "": strteile[3].append(str_val_alt2)
                            elif ii==1:
                                strteile[0].append(str_val)
                                if str_val_alt2 != '<END>' and str_val_alt2 != "" and secondfill: strteile[1].append(str_val_alt2)
                                strteile[2].append(str_val)
                                if str_val_alt2 != '<END>' and str_val_alt2 != "" and secondfill: strteile[3].append(str_val_alt2)
                            else:
                                strteile[0].append(str_val)
                                strteile[1].append(str_val)
                                strteile[2].append(str_val)
                                strteile[3].append(str_val)

                        # with this loop, all 4 possible text values (text1, text2 etc. ) are added to conds [colid,op,text2]

                        for jj in range(textstringnum):
                            conelement = list(cur_cond)
                            strvariant = merge_tokens(strteile[jj], raw_q[b]) # sucks!
                            strvariant = merge_tokens_v2(strteile[jj])
                            conelement.append(strvariant)
                            if strvariant != "": condblock[bid][jj].append(conelement)

                            #for the alternative selection
                            conelementv2 = list(cur_cond_v2)
                            conelementv2.append(strvariant)
                            if strvariant != "": condblock[bid][jj+textstringnum].append(conelementv2)

                # print "finsished building the elements"

                # now BUILT the cond queries:
                queries = []
                for ai in cur_arglist['agg']:
                    for si in cur_arglist['sel']:
                        for bi in range(len(condblock)):
                            if all(len(x)==0 for x in condblock[bi]):
                                continue
                            uniques = []
                            for vi in range(textstringnum*selvariation):
                                if condblock[bi][vi] not in uniques:
                                    uniques.append(condblock[bi][vi])
                            for co in uniques:
                                qu = {}
                                qu["agg"] = ai
                                qu["sel"] = si
                                qu["conds"] = co
                                queries.append(qu)
                # print "finished building the queries"
                ret_querylist.append(queries)
                # ----

                for idx in range(cond_num):
                    cur_cond = []
                    cur_cond.append(max_idxes[idx])
                    cur_cond.append(np.argmax(cond_op_score[b][idx]))
                    cur_cond_str_toks = []
                    for str_score in cond_str_score[b][idx]:
                        str_tok = np.argmax(str_score[:len(all_toks)])
                        str_val = all_toks[str_tok]
                        if str_val == '<END>':
                            break
                        cur_cond_str_toks.append(str_val)
                    cur_cond.append(merge_tokens(cur_cond_str_toks, raw_q[b]))
                    cur_query['conds'].append(cur_cond)
            ret_queries.append(cur_query)

        return ret_queries,ret_querylist

    def argmaxlist(self,werte,maximum=4):
        pass