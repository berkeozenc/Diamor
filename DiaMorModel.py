import base64
import datetime, os, time, stat
import urllib.parse
import json
from html.parser import HTMLParser
from xml.dom import minidom

import zlib

import re


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

class DiaMorModel:

    def __init__(self):
        self.projectPath = ""
        self.xmlFileName = "Not Found"
        self.lexiconFileName = "Not Found"
        self.twolFileNameList = list()
        self.lexionFileLMD = ""
        self.alphabeth = list()
        self.multichars = list()
        self.edges = list()
        self.vertices = list()
        self.vertexSet = {}

    def save(self):
        confFile = open(self.projectPath+"/project.conf","w")
        conf = self.convertToJSON()
        json.dump(conf, confFile)
        '''
        confFile.write("xml::"+self.xmlFileName+"\n")
        confFile.write("lex::"+self.lexiconFileName+"," + self.lexionFileLMD+"\n")
        confFile.write("twol::")
        for twolIndex in range(0,len(self.twolFileNameList)-1):
            confFile.write(str(self.twolFileNameList[twolIndex][0]) + " " + self.twolFileNameList[twolIndex][1] + ",")
        confFile.write(str(self.twolFileNameList[twolIndex+1][0]) + " " + self.twolFileNameList[twolIndex+1][1])
        confFile.write("\n")
        '''
        confFile.close()

    def clearTwolList(self):
        self.twolFileNameList.clear()

    def convertToJSON(self):
        conf = {}
        conf["path"] = self.projectPath
        conf["xml"] = self.xmlFileName
        conf["lexicon"] = self.lexiconFileName
        conf["lexicon_LMD"] = self.lexionFileLMD
        conf["twol"] = list()
        for twolFile in self.twolFileNameList:
            conf["twol"].append(twolFile)
        #conf_json = json.dumps(conf)
        return conf

    def load(self):
        confFile = open(self.projectPath + "/project.conf", "r")
        conf = json.load(confFile)
        self.projectPath = conf["path"]
        self.xmlFileName = conf["xml"]
        self.lexiconFileName = conf["lexicon"]
        self.lexionFileLMD = conf["lexicon_LMD"]
        self.twolFileNameList = conf["twol"]
        '''
        lines = confFile.readlines()
        for l in lines:
            l = l.replace("\n","")
            if "xml:" in l:
                self.xmlFileName = l.split("::")[1]
            elif "lex:" in l:
                self.lexiconFileName = l.split("::")[1].split(",")[0]
                self.lexionFileLMD = l.split("::")[1].split(",")[1]
            elif "twol:" in l:
                twolList = l.split("::")[1].split(",")
                for twol in twolList:
                    state, fileName = twol.split(" ")
                    self.twolFileNameList.append((state, fileName))
        '''
        confFile.close()
    def writeDummyTwol(self):
        dummyTwolFile = open(self.projectPath+"/dummy.twol", "w", encoding="utf-8")
        self.signTheFile(dummyTwolFile)
        dummyTwolFile.write('Alphabet\n\n')
        for a in self.alphabeth:
            dummyTwolFile.write(a + " ")
        dummyTwolFile.write("\n")
        for mc in self.multichars:
            dummyTwolFile.write(mc + " ")
        dummyTwolFile.write(' ;\n\nRules\n\n"Dummy Rule"\n : <=> _ ;')
        dummyTwolFile.close()
        #!Alphabet comes here!\n\nRules\n\n"Dummy Rule"\n : <=> _ ;')

    def signTheFile(self, file):
        file.write("\n! Generated by DiaMor @ " + datetime.datetime.now().strftime("%d-%m-%Y %H:%M") + "\n\n")

    def getEnableTwolList(self):
        enabledTwol = list()
        for f in self.twolFileNameList:
            if f[0] == "2" or f[0] == 2:
                enabledTwol.append(f[1])
        return enabledTwol

    def writeMakeFile(self):
        # if num on twols > 2 : lex + num of twols + num of twols-1 + lex and twol + inverse + create analyze
        # if num on twols = 2 : lex + num of twols + 1 +
        makeFile = open(self.projectPath+"/makefile", "w", encoding="utf-8")
        makeFile.write("comp: lexCompile ")

        enabledTwol = self.getEnableTwolList()
        #print(self.twolFileNameList)
        for et in enabledTwol:
            twolName = et.split(".")[0]
            makeFile.write(twolName+"Compile ")

        if len(enabledTwol) > 1:
            makeFile.write("phon1 ")
            for i in range(2,len(enabledTwol)):
                makeFile.write("phon" + str(i) + " ")

        makeFile.write("combine inverse createAnalyzer\n\n")

        makeFile.write("lexCompile: words.lexc morphotactics.lexc\n\t")
        makeFile.write("hfst-lexc words.lexc morphotactics.lexc -o morphotactics.hfst\n\n")

        if len(enabledTwol) == 1:
            twolName = enabledTwol[0].split(".")[0]
            makeFile.write(twolName + "Compile: " + enabledTwol[0] + "\n\t")
            makeFile.write("hfst-twolc -R -i " + et + " -o phon1.hfst\n\n")
        else:
            for et in enabledTwol:
                twolName = et.split(".")[0]
                makeFile.write(twolName+"Compile: "+et+"\n\t")
                makeFile.write("hfst-twolc -R -i " + et + " -o " + twolName + ".hfst\n\n")

        lastPhon = "phon"+str(1)+".hfst"
        if len(enabledTwol) > 1:
            makeFile.write("phon1: " + enabledTwol[0].replace("twol","hfst") + " " + enabledTwol[1].replace("twol","hfst") + "\n\t")
            makeFile.write("hfst-compose-intersect -1 " + enabledTwol[0].replace("twol","hfst") + " -2 " + enabledTwol[1].replace("twol","hfst") + " -o phon1.hfst\n\n")
            for i in range(2,len(enabledTwol)):
                lastPhon = "phon" + str(i) + ".hfst"
                makeFile.write("phon" + str(i) + ": phon" + str(i-1) + ".hfst " + enabledTwol[i].replace("twol","hfst") + "\n\t")
                makeFile.write("hfst-compose-intersect -1 phon" + str(i-1) + ".hfst -2 " + enabledTwol[i].replace("twol","hfst") + " -o phon" + str(i) + ".hfst\n\n")



        makeFile.write("combine: morphotactics.hfst " + lastPhon + "\n\t")
        makeFile.write("hfst-compose-intersect -1 morphotactics.hfst -2 " + lastPhon + " -o combined.hfst\n\n")

        makeFile.write("inverse: combined.hfst\n\t")
        makeFile.write("hfst-invert -i combined.hfst -o inverseCombined.hfst\n\n")

        makeFile.write("createAnalyzer: inverseCombined.hfst\n\t")
        makeFile.write("hfst-fst2fst -O -i inverseCombined.hfst -o analyze.ol\n\n")


        # if num on twols > 2 : lex + num of twols + num of twols-1 + lex and twol + inverse + create analyze
        # if num on twols = 2 : lex + num of twols + 1 +
        makeFile.close()

    def generateAlphabet(self):
        currentLMD = self.getLMD()
        if self.lexionFileLMD == "":
            self.lexionFileLMD = currentLMD.strftime('%Y-%m-%d %H:%M:%S')
            self.createWordslexc()
        else:
            savedLMF = datetime.datetime.strptime(self.lexionFileLMD, '%Y-%m-%d %H:%M:%S')
            if currentLMD > savedLMF :
                self.lexionFileLMD = currentLMD.strftime('%Y-%m-%d %H:%M:%S')
                self.createWordslexc()

    def getLMD(self):
        modificationTime = os.path.getmtime(self.projectPath + "/" + self.lexiconFileName)
        return datetime.datetime.fromtimestamp(modificationTime)#.strftime('%Y-%m-%d %H:%M:%S')

    def createWordslexc(self):
        print("Generating alphabeth and words.lexc")
        txt = open(self.projectPath + "/" + self.lexiconFileName, "r", encoding="utf-8")
        lexcString = "LEXICON Root \n\n"
        txtLines = txt.readlines()
        for line in txtLines:
            if " " in line:
                word, state = line.split(" ")
                self.getLetters(word)
                lexcString = lexcString + self.putEscape(word) + " " + state.replace("\n","") + " ;\n"
        mcString = "Multichar_Symbols\n\n"
        for mc in self.multichars:
            mcString += mc + "\n"
        mcString += "\n\n"
        lexcString = mcString + lexcString
        lexc = open(self.projectPath + "/words.lexc", "w", encoding="utf-8")
        lexc.write(lexcString)
        lexc.close()
        #print(self.alphabeth)
        #print(len(self.alphabeth))
        #print(self.multichars)

    def getLetters(self, word):
        notLetter = ['{','}','(',')']
        inMultichar = False
        multichar = ""
        for i in range(0, len(word)):
            char = word[i]
            if not inMultichar and char not in notLetter:
                if char not in self.alphabeth:
                    self.alphabeth.append(char)
            elif char == "{":
                inMultichar = True
                multichar += char
            elif char == "}":
                inMultichar = False
                multichar += char
                try:
                    self.addMultichar(multichar)
                except:
                    print("wew")
                multichar = ""
            else:
                multichar += char

    def putEscape(self, str):
        str = str.replace("<", "%<")
        str = str.replace(">", "%>")
        str = str.replace("-", "%-")
        str = str.replace("(", "%(")
        str = str.replace(")", "%)")
        str = str.replace("}", "%}")
        str = str.replace("{", "%{")
        #str = str.replace(":","%:",1)
        str = re.sub(r"(%<.+):(.+%>)",r"\1%:\2",str)
        return str

    def xml2lexc(self):
        self.readXML()
        self.generateGM()
        self.generateLEXC()

    def readXML(self):
        mydoc = minidom.parse(self.projectPath + "/" +self.xmlFileName)
        items = mydoc.getElementsByTagName('diagram')
        encodedXml = items[0].childNodes[0].data
        decodedXML = self.decodeXML(encodedXml)
        mydoc = minidom.parseString(decodedXML)
        items = mydoc.getElementsByTagName('mxCell')
        for i in items:
            if i.attributes['id'].value not in [0, 1]:
                if 'vertex' in i.attributes:
                    if self.vertexSet.get(self.stripStyle(i.attributes['value'].value)) is None:
                        self.vertexSet[self.stripStyle(i.attributes['value'].value)] = i
                        #print(self.stripStyle(i.attributes['value'].value) + " added to Vertex List")
                    self.vertices.append(i)
                if 'edge' in i.attributes:
                    self.edges.append(i)
        self.generateGM()
        #print(self.graphMatrix)

    def decodeXML(self, encoded):
        res = base64.b64decode(encoded)
        decodedXML = urllib.parse.unquote(zlib.decompress(res, -15).decode("utf-8"))
        return decodedXML

    def stripStyle(self, str):
        s = MLStripper()
        s.feed(str)
        return s.get_data()

    def ID2Index(self, ID, vertices, set):
        for index in range(0, len(vertices)):
            vertex = vertices[index]
            if vertex.attributes['id'].value == ID:
                #print(self.stripStyle(vertex.attributes['value'].value) + " " + str(list(set.keys()).index(self.stripStyle(vertex.attributes['value'].value))))
                return list(set.keys()).index(self.stripStyle(vertex.attributes['value'].value))
        return -1

    def generateGM(self):
        self.graphMatrix = [[0 for _ in range(len(self.vertexSet))] for _ in range(len(self.vertexSet))]
        for e in self.edges:
            fromID = e.attributes['source'].value
            fromIndex = self.ID2Index(fromID, self.vertices, self.vertexSet)
            toID = e.attributes['target'].value
            toIndex = self.ID2Index(toID, self.vertices, self.vertexSet)
            #print("EDGE from: " + str(fromIndex) + " to: " + str(toIndex) + " value: " + self.stripStyle(e.attributes['value'].value))
            if 'value' in e.attributes:
                value = self.stripStyle(e.attributes['value'].value)
                #value = re.sub("([\-\w\)])<", r"\1;<", value)
                self.getMultichars(value)
                self.graphMatrix[fromIndex][toIndex] = value
            else:
                self.graphMatrix[fromIndex][toIndex] = " "

    def getMultichars(self, str):
        try:
            strList = str.split(";")
            for s in strList:
                s_split = s.split(":")
                abs = ""
                for s_splitIdx in range(0, len(s_split) - 1):
                    if len(s_split) > 2 and s_splitIdx == 0:
                        abs += s_split[s_splitIdx] + ":"
                    else:
                        abs += s_split[s_splitIdx]
                self.addMultichar(abs)
                inMultichar = False
                isNormalBracet = False
                suffix = s_split[len(s_split)-1]
                multichar = ""
                for i in range(0, len(suffix)):
                    if suffix[i] == "(" and not inMultichar:
                        isNormalBracet = True
                        inMultichar = True
                        multichar += suffix[i]
                    elif suffix[i] == "{" and not inMultichar:
                        inMultichar = True
                        multichar += suffix[i]
                    elif suffix[i] == ")" and inMultichar and isNormalBracet:
                        isNormalBracet = False
                        inMultichar = False
                        multichar += suffix[i]
                        self.addMultichar(multichar)
                        multichar = ""
                    elif suffix[i] == "}" and inMultichar and not isNormalBracet:
                        inMultichar = False
                        multichar += suffix[i]
                        self.addMultichar(multichar)
                        multichar = ""
                    elif inMultichar:
                        multichar += suffix[i]
                    else:
                        if suffix[i] not in self.alphabeth:
                            self.alphabeth.append(self.putEscape(suffix[i]))
        except:
            print("getMultichars")

    def addMultichar(self, mc):
        mc = self.putEscape(mc)
        if mc not in self.multichars:
            self.multichars.append(mc)

    def generateLEXC(self):
        lexcFile = open(self.projectPath + "/morphotactics.lexc", "w", encoding="utf-8")
        lexcFile.write("Multichar_Symbols\n\n")
        for mc in self.multichars:
            lexcFile.write(mc + "\n")
        for i in range(0, len(self.graphMatrix)):
            lexcFile.write("\n")
            lexcFile.write("\n")
            stateName = self.stripStyle(list(self.vertexSet.values())[i].attributes['value'].value)
            lexcFile.write("LEXICON " + stateName + "\n")
            lexcFile.write("\n")
            for j in range(0, len(self.graphMatrix[i])):
                if self.graphMatrix[i][j] != 0:
                    if self.graphMatrix[i][j] != " ":
                        transections = self.graphMatrix[i][j].split(";")
                        to = self.stripStyle(list(self.vertexSet.values())[j].attributes['value'].value)
                        # lexcFile.write("*****" + graphMatrix[i][j] + "\n")
                        for t in transections:
                            lexcFile.write(self.putEscape(t) + " ")
                            lexcFile.write(to + ";\n")
                    else:
                        to = self.stripStyle(list(self.vertexSet.values())[j].attributes['value'].value)
                        lexcFile.write(to + ";\n")

            if "doubleEllipse" in list(self.vertexSet.values())[i].attributes['style'].value:
                lexcFile.write("#;\n")
        lexcFile.close()


