import argparse
import os

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QListWidget, QTableWidgetItem
from PyQt5.QtWidgets import QTableWidget
from nqlpredgui import Ui_MainWindow
import sys
import pandas as pd
import json
from collections import OrderedDict
from importlib import reload
from sqlnet.suggcreator import create_suggestions,parse_nql
# os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = "D:/Programme/Anaconda3/Library/plugins/platforms"

import torch
from sqlnet.model.sqlnet import SQLNet
from sqlnet.utils import *
# -----
parser = argparse.ArgumentParser()
parser.add_argument('--toy', action='store_true',
                    help='If set, use small data; used for fast debugging.')
parser.add_argument('--ca', action='store_true',default=True,
                    help='Use conditional attention.')
parser.add_argument('--dataset', type=int, default=0,
                    help='0: original dataset, 1: re-split dataset')
parser.add_argument('--rl', action='store_true',
                    help='Use RL for Seq2SQL.')
parser.add_argument('--baseline', action='store_true',
                    help='If set, then test Seq2SQL model; default is SQLNet model.')
parser.add_argument('--train_emb', action='store_true',
                    help='Use trained word embedding for SQLNet.')
args = parser.parse_args()

train_emb = False
N_word = 300
B_word = 42

USE_SMALL = False
GPU = True
BATCH_SIZE = 2  # TODO: Back to 64
TEST_ENTRY = (True, True, True)  # (AGG, SEL, COND)

sql_data, table_data, val_sql_data, val_table_data, \
test_sql_data, test_table_data, \
TRAIN_DB, DEV_DB, TEST_DB = load_dataset(
    0, use_small=USE_SMALL)

word_emb = load_word_emb('glove/glove.%dB.%dd.txt' % (B_word, N_word), \
                         load_used=True, use_small=USE_SMALL)  # load_used can speed up loading


model = SQLNet(word_emb, N_word=N_word, use_ca=True, gpu=GPU,
                   trainable_emb=True)

if train_emb:
    agg_m, sel_m, cond_m, agg_e, sel_e, cond_e = best_model_name(args)
    print("Loading from %s" % agg_m)
    model.agg_pred.load_state_dict(torch.load(agg_m))
    print("Loading from %s" % sel_m)
    model.sel_pred.load_state_dict(torch.load(sel_m))
    print("Loading from %s" % cond_m)
    model.cond_pred.load_state_dict(torch.load(cond_m))
    print("Loading from %s" % agg_e)
    model.agg_embed_layer.load_state_dict(torch.load(agg_e))
    print("Loading from %s" % sel_e)
    model.sel_embed_layer.load_state_dict(torch.load(sel_e))
    print("Loading from %s" % cond_e)
    model.cond_embed_layer.load_state_dict(torch.load(cond_e))
else:
    agg_m, sel_m, cond_m = best_model_name(args)
    print("Loading from %s" % agg_m)
    model.agg_pred.load_state_dict(torch.load(agg_m))
    print("Loading from %s" % sel_m)
    model.sel_pred.load_state_dict(torch.load(sel_m))
    print("Loading from %s" % cond_m)
    model.cond_pred.load_state_dict(torch.load(cond_m))





# ---------------

def filltable(df : pd.DataFrame, table : QTableWidget):
    table.setHorizontalHeaderLabels(df.columns.tolist())
    table.setRowCount(df.shape[0])
    table.setColumnCount(df.shape[1])

    for i, row in df.iterrows():
        line = list(row)
        for j,element in enumerate(line):
            table.setItem(i, j, QTableWidgetItem(element))

def createtableasdf():
    df = pd.DataFrame(columns=["Cola", "Colb", "ColC", "ColD"])
    for i in range(7):
        line = {}
        line["Cola"] = "Test" + str(i)
        line["Colb"] = "Tesasft" + str((i*2)%5+3)
        line["ColC"] = "Tesgst" + str((i*7)%3+6)
        line["ColD"] = "Tessdt" + str((i*18)%7+7)
        df = df.append(line, ignore_index=True)
    return df

def filltablelist(tables : OrderedDict, liste = QListWidget):
    for key, value in tables.items():
        if "page_title" not in value.keys():
            value["page_title"] = "N.A."
        liste.addItem(key+"\t"+value["page_title"])


def builddfFromwiki(td : dict):
    cols = td["header"]
    df = pd.DataFrame(columns=cols)
    for i,col in enumerate(cols):
        df[col] = [str(zeile[i]) for zeile in td["rows"]]
    return df

def loadtables():
    tables =OrderedDict()
    with open("data/test_tok.tables.jsonl") as f:
        content = f.readlines()[0:20]
    for zeile in content:
        tdict = {}
        zeile = zeile.strip()
        zd = json.loads(zeile)
        zd["df"] = builddfFromwiki(zd)
        tables[zd["id"]] = zd
    return tables


class ApplicationWindow(QtWidgets.QMainWindow):
    df : pd.DataFrame
    tables = []
    currenttable = {}
    result = {}
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.tables = loadtables()
        self.df = createtableasdf()
        filltable(self.df,self.ui.tableWidget)
        filltablelist(self.tables,self.ui.listTables)
        self.ui.listTables.itemClicked.connect(self.tableclicked)
        self.ui.listTables.item(0).setSelected(True)
        self.tableclicked(self.ui.listTables.item(0))
        self.ui.listvorschlaege.itemClicked.connect(self.suggestionclicked)
        self.ui.btnConvert.clicked.connect(self.processinput)
        self.ui.btnRunNQL.clicked.connect(lambda : self.ui.txtResultDSL.setText(str(parse_nql(self.ui.textNQL.toPlainText(),self.currenttable))))


    def tableclicked(self,item):
        tname = item.text().split("\t")[0]
        self.currenttable = self.tables[tname]
        df = self.tables[tname]["df"]
        filltable(df,self.ui.tableWidget)
        print("angeklickt")

    def suggestionclicked(self,item):
        tname = item.text()
        self.ui.textNQL.setText(tname)
        wert = self.result[tname]
        self.ui.txtResultDSL.setText(str(wert))


    def processinput(self):
        txt = self.ui.txtNL.toPlainText()
        self.result : dict = create_suggestions(model,txt,self.currenttable)
        self.ui.listvorschlaege.clear()
        for key, value in self.result.items():
            self.ui.listvorschlaege.addItem(key)
        # # self.ui.txtNL = StreamTextEdit(self.ui.centralwidget)
        # self.ui.btnConvert.clicked.connect(lambda x: processInputNL(self.ui.txtNL.toPlainText()))
        # self.ui.txtNL.outputfeld = self.ui.txtResultDSL
        # self.ui.txtNL.setSuggestlist(self.ui.listvorschlaege)
        #
        # self.ui.textEdit.setSuggestlist(self.ui.listvorschlaege)
        # self.ui.textEdit.outputfeld = self.ui.txtResultDSL
        #
        # self.ui.txtNL.startBackgroundThread()
        # self.ui.btnConvert.setVisible(False)

def main():
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()