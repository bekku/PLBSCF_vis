from django.shortcuts import render
import csv
import io
import numpy as np
import pandas as pd
import copy
from collections import OrderedDict



def index(request):
	return render(request, 'plbscf/index.html')


def PL_Create(MOTOCHO_DF, PL_KAMOKU, KAMOKU_GROUP):
	# PLで扱う全ての勘定科目をリストでまとめる
	plele_list = []
	for plele in PL_KAMOKU:
		plele_list += KAMOKU_GROUP[plele]

	# 総勘定元帳のPLを勘定科目グループ化(sum)と、勘定科目の貸方-借方金額を計算して列として追加
	PL_KAMOKUSUM = MOTOCHO_DF[MOTOCHO_DF["勘定科目"].isin(plele_list)].groupby("勘定科目").sum()[["借方金額", "貸方金額"]]
	PL_KAMOKUSUM["差分"] = PL_KAMOKUSUM["貸方金額"] - PL_KAMOKUSUM["借方金額"]

	tortal_sum = 0
	toral_name = ["", "売上総利益", "営業利益", "経常利益", "", "", "税引前当期純利益", "当期純利益"]
	# PL_RESULTには、{売上高：90~, 売上原価:{期首商品棚卸高:10~, }}の形になる。
	PL_RESULT = OrderedDict()
	for enunum, plele in enumerate(PL_KAMOKU):
		Pl_ByKamoku = PL_KAMOKUSUM.reindex(index = KAMOKU_GROUP[plele])
		Pl_ByKamoku = Pl_ByKamoku.fillna(0)
			#勘定グループに属する勘定科目とその差分をPL_RESULTに追加
		PLELE_LIST_DICT = OrderedDict(Pl_ByKamoku["差分"])

		if KAMOKU_GROUP[plele] != []:
			tortal_sum += Pl_ByKamoku["差分"].sum()
			#勘定グループの総和(必要ない可能性あり)
			PLELE_LIST_DICT[plele + "合計"] = Pl_ByKamoku["差分"].sum()

		PL_RESULT[plele] = PLELE_LIST_DICT

		if toral_name[enunum] !="":
			# 各利益(経常利益、営業利益など)を計算して追加
			PL_RESULT[toral_name[enunum]] = float(tortal_sum)

	return PL_RESULT

def BS_Create(MOTOCHO_DF, BS_KAMOKU, KAMOKU_GROUP):
	# PLで扱う全ての勘定科目をリストでまとめる
	BS_RESULTS = dict()
	BS_RESULTS["資産"] = dict()
	BS_RESULTS["負債"] = dict()
	bsele_list = []
	for bsele in BS_KAMOKU:
		bsele_list += KAMOKU_GROUP[bsele]

	# 総勘定元帳のPLを勘定科目グループ化(sum)と、勘定科目の貸方-借方金額を計算して列として追加
	BS_KAMOKUSUM = MOTOCHO_DF[MOTOCHO_DF["勘定科目"].isin(bsele_list)].groupby("勘定科目").sum()[["借方金額", "貸方金額"]]
	BS_KAMOKUSUM["差分"] = BS_KAMOKUSUM["貸方金額"] - BS_KAMOKUSUM["借方金額"]


	tortal_sum = 0
	# BS_RESULTには、{売上高：90~, 売上原価:{期首商品棚卸高:10~, }}の形になる。
	BS_RESULT = OrderedDict()
	for enunum, bsele in enumerate(BS_KAMOKU):
		Bs_ByKamoku = BS_KAMOKUSUM.reindex(index = KAMOKU_GROUP[bsele])
		Bs_ByKamoku = Bs_ByKamoku.fillna(0)

		# 資産は借方がプラスなので、借方-貸方にする。
		if enunum in [0,1,2]:
			Bs_ByKamoku*=-1

		#勘定グループに属する勘定科目とその差分をBS_RESULTに追加
		BSELE_LIST_DICT = OrderedDict(Bs_ByKamoku["差分"])

		if KAMOKU_GROUP[bsele] != []:
			tortal_sum += Bs_ByKamoku["差分"].sum()
			#勘定グループの総和(必要ない可能性あり)
			BSELE_LIST_DICT[bsele + "合計"] = Bs_ByKamoku["差分"].sum()

		BS_RESULT[bsele] = BSELE_LIST_DICT

		if enunum in [0,1,2]:
			BS_RESULTS["資産"][bsele] = BS_RESULT[bsele]
		else:
			BS_RESULTS["負債"][bsele] = BS_RESULT[bsele]

		# 資産と負債の合計値の出力のために追加している。
		if enunum == 2:
			BS_RESULTS["資産"]["資産合計"] = float(tortal_sum)
			tortal_sum = 0
		elif enunum == 4:
			BS_RESULTS["負債"]["負債合計"] = float(tortal_sum)
			tortal_sum = 0


	return BS_RESULTS


# <改善>
# cf_dfを構築する関数を抽出した方が良い。
# PLBSCFの共通部分を関数化して抽出した方が良い
def CF_Create(MOTOCHO_DF, CF_EIGYOU, CF_TOUSHI, CF_ZAIMU, CF_KAMOKU, KAMOKU_GROUP):
	# 勘定科目と相手勘定科目のCFグループ(営業, 投資, 財務)を確認
	# 営業 - 投資の場合, 投資に
	# 営業 - 財務の場合, 財務に
	cf_df = MOTOCHO_DF.copy()

	# 営業、投資、財務のグループ作成
	CF_GROUP_E = []
	CF_GROUP_T = []
	CF_GROUP_Z = []
	for enunum, cfele in enumerate(CF_KAMOKU):
		if cfele == CF_KAMOKU[0]:
			add_list = CF_GROUP_E
		elif cfele == CF_KAMOKU[len(CF_EIGYOU)]:
			add_list = CF_GROUP_T
		elif cfele == CF_KAMOKU[len(CF_TOUSHI)]:
			add_list = CF_GROUP_Z
		add_list += KAMOKU_GROUP[cfele]
	CF_GROUP_E = set(CF_GROUP_E)
	CF_GROUP_T = set(CF_GROUP_T)
	CF_GROUP_Z = set(CF_GROUP_Z)

	# 全ての総勘定元帳に対して、勘定科目と相手勘定科目を比較して、営業-投資or財務の時は営業を上書きする。
	# 上書きする値は、投資or財務_営業名となる。
	for num in range(len(cf_df)):
		tmp = cf_df[["勘定科目", "相手勘定科目"]].loc[num]
		KANJOU = tmp[0]
		AITEKANJOU = tmp[1]
		KANJOU_Group = -1
		AITEKANJOU_Group = -1

	# 勘定科目がどのグループに属するか
		if KANJOU in CF_GROUP_E:
			KANJOU_Group = "営業"
		elif KANJOU in CF_GROUP_T:
			KANJOU_Group = "投資"
		elif KANJOU in CF_GROUP_Z:
			KANJOU_Group = "財務"

	# 相手勘定科目がどのグループに属するか
		if AITEKANJOU in CF_GROUP_E:
			AITEKANJOU_Group = "営業"
		elif AITEKANJOU in CF_GROUP_T:
			AITEKANJOU_Group = "投資"
		elif AITEKANJOU in CF_GROUP_Z:
			AITEKANJOU_Group = "財務"


	# 上書きと、グループに追加
		if AITEKANJOU_Group == "営業":
			if KANJOU_Group in ["財務", "投資"]:
				cf_df.loc[num, "相手勘定科目"] = KANJOU_Group + "_" + str(cf_df["相手勘定科目"].loc[num])
				KAMOKU_GROUP[KANJOU_Group + "CFその他"].append(str(cf_df["相手勘定科目"].loc[num]))

				if KANJOU_Group == "財務":
					CF_GROUP_Z.add(str(cf_df["相手勘定科目"].loc[num]))
				else:
					CF_GROUP_T.add(str(cf_df["相手勘定科目"].loc[num]))

		if KANJOU_Group == "営業":
			if AITEKANJOU_Group in ["財務", "投資"]:
				cf_df.loc[num, "勘定科目"] = AITEKANJOU_Group + "_" + str(cf_df["勘定科目"].loc[num])
				KAMOKU_GROUP[AITEKANJOU_Group + "CFその他"].append(str(cf_df["勘定科目"].loc[num]))

				if AITEKANJOU_Group == "財務":
					CF_GROUP_Z.add(str(cf_df["勘定科目"].loc[num]))
				else:
					CF_GROUP_T.add(str(cf_df["勘定科目"].loc[num]))



		KAMOKU_GROUP["投資CFその他"] = list(set(KAMOKU_GROUP["投資CFその他"]))
		KAMOKU_GROUP["財務CFその他"] = list(set(KAMOKU_GROUP["財務CFその他"]))
	# CFで扱う全ての勘定科目をリストでまとめる
	cfele_list = []
	for cfele in CF_KAMOKU:
		cfele_list += KAMOKU_GROUP[cfele]
	# 総勘定元帳のCFを勘定科目グループ化(sum)と、勘定科目の貸方-借方金額を計算して列として追加
	CF_KAMOKUSUM = cf_df[cf_df["勘定科目"].isin(cfele_list)].groupby("勘定科目").sum()[["借方金額", "貸方金額"]]
	CF_KAMOKUSUM["差分"] = CF_KAMOKUSUM["貸方金額"] - CF_KAMOKUSUM["借方金額"]

	tortal_sum = 0
	CF_ETZ_LIST = []
	CF_RESULTS = dict()
	CF_names = ["営業CF", "投資CF", "財務CF"]
	CF_NUM = 0
	CF_RESULT = OrderedDict()

	for enunum, cfele in enumerate(CF_KAMOKU):
		CF_ByKamoku = CF_KAMOKUSUM.reindex(index=KAMOKU_GROUP[cfele])
		CF_ByKamoku =  CF_ByKamoku.fillna(0)
		if cfele == CF_KAMOKU[len(CF_EIGYOU)]:
			CF_NUM = 1
		elif cfele == CF_KAMOKU[len(CF_TOUSHI)]:
			CF_NUM = 2

		CFELE_LIST_DICT = OrderedDict(CF_ByKamoku["差分"])
		if KAMOKU_GROUP[cfele] != []:
			tortal_sum += CF_ByKamoku["差分"].sum()
			CFELE_LIST_DICT[cfele + "合計"] = CF_ByKamoku["差分"].sum()
		CF_RESULT[cfele] = CFELE_LIST_DICT

		if enunum+1 in [len(CF_EIGYOU), len(CF_TOUSHI), len(CF_ZAIMU)]:
			CF_RESULT["合計" + CF_names[CF_NUM]] = float(tortal_sum)
			CF_RESULTS[CF_names[CF_NUM]] = copy.deepcopy(CF_RESULT)
			tortal_sum = 0
			CF_RESULT = OrderedDict()

	return CF_RESULTS


# csvをPLBSCFを作成する
def csv_to_PLBSCF(request):
	if 'csv' in request.FILES:
		MOTOCHO_DF = pd.read_csv(request.FILES['csv'].file, encoding="cp932")
	#-----------------科目グループ作成-----------------
	KAMOKU_GROUP = dict()
	# -----------------------BS-----------------------
	KAMOKU_GROUP["流動資産"] = ['現金', '普通預金', '売掛金', '商品', '前払金', '立替金', '短期貸付金', '未収入金', '仮払金', '仮払消費税']
	KAMOKU_GROUP["流動資産_現金及び預金"] = ['現金', '普通預金']
	KAMOKU_GROUP["流動資産_売上債権"] = ['売掛金']
	KAMOKU_GROUP["流動資産_棚卸資産"] = ['商品']
	KAMOKU_GROUP["流動資産_その他の流動資産"] = ['前払金', '立替金', '短期貸付金', '未収入金', '仮払金', '仮払消費税']

	KAMOKU_GROUP["固定資産"] = ['建物', '工具器具備品', '土地', '長期前払費用', '預託金', '保険積立金']
	KAMOKU_GROUP["固定資産_有形固定資産"] = ['建物', '工具器具備品', '土地']
	KAMOKU_GROUP["固定資産_無形固定資産"] = []
	KAMOKU_GROUP["固定資産_投資その他の資産"] = ['長期前払費用', '預託金', '保険積立金']

	KAMOKU_GROUP["繰越資産"] = []

	KAMOKU_GROUP["流動負債"] = ['短期借入金', '未払金', '預り金', '未払法人税等', '仮受消費税']
	KAMOKU_GROUP["流動負債_仕入れ債務"] = []
	KAMOKU_GROUP["流動負債_その他の流動負債"] = ['短期借入金', '未払金', '預り金', '未払法人税等', '仮受消費税']

	KAMOKU_GROUP["固定負債"] = ['長期借入金']
	# ------------------------------------------------
	# -----------------------PL-----------------------
	KAMOKU_GROUP["売上高"] = ['売上高']

	KAMOKU_GROUP["売上原価"] = ['期首商品棚卸高', '仕入高', '期末商品棚卸高']

	KAMOKU_GROUP["販売費及び一般管理費"] = ['役員報酬', '給料賃金', '法定福利費', '福利厚生費', '研修採用費', '業務委託料', '荷造運賃', '広告宣伝費', '接待交際費', '旅費交通費', '通信費', '水道光熱費', '修繕費', '備品・消耗品費', '地代家賃', '保険料', '租税公課', '支払手数料', '支払報酬', '会議費', '新聞図書費', '雑費']
	KAMOKU_GROUP["販売費及び一般管理費_人件費"] = ['役員報酬', '給料賃金', '法定福利費', '福利厚生費', '研修採用費', '業務委託料']
	KAMOKU_GROUP["販売費及び一般管理費_販売費及び一般管理費"] = ['荷造運賃', '広告宣伝費', '接待交際費', '旅費交通費', '通信費', '水道光熱費', '修繕費', '備品・消耗品費', '地代家賃', '保険料', '租税公課', '支払手数料', '支払報酬', '会議費', '新聞図書費', '雑費']

	KAMOKU_GROUP["営業外収益"] = ['受取利息', '雑収入']

	KAMOKU_GROUP["営業外費用"] = ['支払利息']

	KAMOKU_GROUP["特別利益"] = []

	KAMOKU_GROUP["特別損失"] = ['固定資産売却損']

	KAMOKU_GROUP["法人税等"] = ['法人税等']

	# CF用科目グループの追加
	KAMOKU_GROUP["営業CFその他"] = []
	KAMOKU_GROUP["投資CFその他"] = []
	KAMOKU_GROUP["財務CFその他"] = []
	#--------------------------------------------------

	# PLBSCFで用いる勘定グループのリスト
	BS_KAMOKU = ["流動資産", "固定資産", "繰越資産", "流動負債", "固定負債"]
	PL_KAMOKU = ["売上高", "売上原価", "販売費及び一般管理費", "営業外収益", "営業外費用", "特別利益", "特別損失", "法人税等"]
	CF_EIGYOU = [
	"売上高", "流動資産_売上債権", "流動負債_仕入れ債務",
	"売上原価", "販売費及び一般管理費", "流動資産_その他の流動資産",
	"流動負債_その他の流動負債", "営業外収益", "営業外費用", "法人税等", "営業CFその他"]
	CF_TOUSHI = CF_EIGYOU + ['固定資産', '繰越資産', "投資CFその他"]
	CF_ZAIMU = CF_TOUSHI+ ['固定負債', "財務CFその他"]
	CF_KAMOKU = CF_ZAIMU

	# PLとBSの作成関数実行
	PL_view = PL_Create(MOTOCHO_DF, PL_KAMOKU, KAMOKU_GROUP)
	BS_view = BS_Create(MOTOCHO_DF, BS_KAMOKU, KAMOKU_GROUP)
	CF_view = CF_Create(MOTOCHO_DF, CF_EIGYOU, CF_TOUSHI, CF_ZAIMU, CF_KAMOKU, KAMOKU_GROUP)
	context = {}
	context['PL_view'] = PL_view
	context['BS_view'] = BS_view
	context['CF_view'] = CF_view
	return render(request, 'plbscf/index.html', {"context":context})
