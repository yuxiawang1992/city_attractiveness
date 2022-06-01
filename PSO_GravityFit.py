# -*- coding: utf-8 -*-

import random
import copy
import math
import pandas as pd
import time

# 地球半径平均值，单位：km
EARTH_RADIUS = 6371.0


# 计算球面两点间的距离
def haveSine(theta):
    v = math.sin(theta / 2)
    return v * v


# 将角度换算为弧度， degrees为角度，return为弧度
def convertDegreesToRadians(degrees):
    return degrees * math.pi / 180


# 计算经纬度之间的距离（公里、千米）
def haveSineDistance(lon1, lat1, lon2, lat2):
    # 用haveSinee公式计算球面两点间的距离
    # 经纬度转换成弧度
    lat1 = convertDegreesToRadians(lat1)
    lon1 = convertDegreesToRadians(lon1)
    lat2 = convertDegreesToRadians(lat2)
    lon2 = convertDegreesToRadians(lon2)
    # 差值
    vLon = abs(lon1 - lon2)
    vLat = abs(lat1 - lat2)
    # h is the great circle distance in radians, great circle就是一个球体上的切面，它的圆心即是球心的一个周长最大的圆
    h = haveSine(vLat) + math.cos(lat1) * math.cos(lat2) * haveSine(vLon)
    distance = 2 * EARTH_RADIUS * math.asin(math.sqrt(h))
    return distance


# 预处理数据函数
def preprocessData(points, flows):
    PointName = []

    for rcd in flows:
        if rcd[0] not in PointName:
            PointName.append(rcd[0])
        if rcd[1] not in PointName:
            PointName.append(rcd[1])

    PointNum = len(PointName)

    # build a matrix for interactions
    # RT part: interaction strength
    # LB part: distance in km

    InterData = [[-1.0 for i in range(PointNum)] for j in range(PointNum)]
    lon1 = -1
    lat1 = -1
    lon2 = -1
    lat2 = -1
    # 只计算有流存在的两个城市的距离
    for rcd in flows:
        n1 = PointName.index(rcd[0])
        for p in points:
            if p[0] == rcd[0]:
                lon1 = p[1]
                lat1 = p[2]
                break
        n2 = PointName.index(rcd[1])
        for p in points:
            if p[0] == rcd[1]:
                lon2 = p[1]
                lat2 = p[2]
                break
        if n1 > n2:
            t = n1
            n1 = n2
            n2 = t
        InterData[n1][n2] = int(rcd[2])
        InterData[n2][n1] = haveSineDistance(lon1, lat1, lon2, lat2)
    ValidPair = len(flows)

    return InterData, PointNum, ValidPair, PointName


# 创建流
def CreateFlows(CitySize, PointNum, beta, InterData):
    for i in range(0, PointNum):
        for j in range(0, i):
            if InterData[i][j] > 0:  # valid pair
                InterData[j][i] = CitySize[i] * CitySize[j] / pow(InterData[i][j], beta)
            else:
                InterData[j][i] = -1


# 抽取流
def ExtractFlowData(InterData, ValidPair, PointNum):
    Data = [0.0] * ValidPair
    Count = 0
    for i in range(0, PointNum):
        for j in range(i + 1, PointNum):
            if InterData[i][j] > 0.0:
                Data[Count] = InterData[i][j]
                Count += 1

    return Data


# 计算一维皮尔森相关系数
def PearsonCoefficient1D(data1, data2, size):
    mean1 = 0.0
    mean2 = 0.0
    i = 0

    while i < size:
        mean1 += data1[i]
        mean2 += data2[i]
        i += 1

    mean1 /= size
    mean2 /= size
    cov1 = 0.0
    cov2 = 0.0
    cov12 = 0.0

    i = 0
    while i < size:
        try:
            cov12 += (data1[i] - mean1) * (data2[i] - mean2)
            cov1 += (data1[i] - mean1) * (data1[i] - mean1)
            cov2 += (data2[i] - mean2) * (data2[i] - mean2)
            i += 1
        except:
            print(i)

    if abs(cov1) < 0.00000001 or abs(cov2) < 0.00000001:
        return 0
    return cov12 / math.sqrt(cov1) / math.sqrt(cov2)


# 粒子群搜索
def PSOSearch(InterData, PointNum, ValidPair, InitialSizes, beta, ParticleNum, SearchRange, w, c1, c2):
    Particles = [[0.0 for i in range(PointNum)] for j in range(ParticleNum)]
    for i in range(0, ParticleNum):
        for j in range(0, PointNum):
            if i == 0:
                Particles[i][j] = InitialSizes[j]
            else:
                Particles[i][j] = InitialSizes[j] + (random.random() * SearchRange / 5 - SearchRange / 10)
            if Particles[i][j] > SearchRange:
                Particles[i][j] = SearchRange
            if Particles[i][j] < 0:
                Particles[i][j] = 0

    # print Particles
    Velocity = [[random.random() * SearchRange - SearchRange / 2 for a in range(PointNum)] for b in range(ParticleNum)]
    # print Velocity

    gBestParticleScore = 0.0
    gBestParticle = [0.0] * PointNum

    pBestParticleScore = [0.0] * ParticleNum
    pBestParticle = [[0.0 for a in range(PointNum)] for b in range(ParticleNum)]

    RealFlowData = ExtractFlowData(InterData, ValidPair, PointNum)

    InterDataTemp = copy.deepcopy(InterData)
    IterCount = 0
    while 1:
        tBestScore = 0
        for i in range(0, ParticleNum):
            CreateFlows(Particles[i], PointNum, beta, InterDataTemp)
            FitData = ExtractFlowData(InterDataTemp, ValidPair, PointNum)

            gof = PearsonCoefficient1D(FitData, RealFlowData, ValidPair)
            if gof > tBestScore:
                tBestScore = gof

            # print gof
            if gof > pBestParticleScore[i]:
                pBestParticleScore[i] = gof
                for j in range(0, PointNum):
                    pBestParticle[i][j] = Particles[i][j]

            if gof > gBestParticleScore:
                gBestParticleScore = gof
                for j in range(0, PointNum):
                    gBestParticle[j] = Particles[i][j]

        # update particles
        maxVelocity = 0
        for i in range(0, ParticleNum):
            nc1 = c1 * random.random()
            nc2 = c2 * random.random()
            for j in range(0, PointNum):
                newVelocity = Velocity[i][j] * w + nc1 * (pBestParticle[i][j] - Particles[i][j]) + \
                              nc2 * (gBestParticle[j] - Particles[i][j])
                # print i,j,c1,c2,Velocity[i][j],newVelocity

                if newVelocity + Particles[i][j] > SearchRange:
                    newVelocity = SearchRange - Particles[i][j]
                if newVelocity + Particles[i][j] < 0:
                    newVelocity = - Particles[i][j]

                if abs(newVelocity) > maxVelocity: maxVelocity = newVelocity

                Velocity[i][j] = newVelocity
                Particles[i][j] += newVelocity
        # print gBestParticleScore, tBestScore, maxVelocity
        IterCount += 1
        if IterCount >= 1000 or maxVelocity < 5 or gBestParticleScore > 0.98:
            break

    return gBestParticleScore, gBestParticle


# 计算每一列的所有值之和，相当于流网络的度
def InitSize(InterData, PointNum):
    Size = [0.0] * PointNum
    for i in range(0, PointNum):
        for j in range(i + 1, PointNum):
            if InterData[i][j] > 0.0:
                Size[i] += InterData[i][j]
                Size[j] += InterData[i][j]
    return Size


def mp(i):
    print(i)


# 主调函数
def gravityFit(points, flows):
    InterData, PointNum, ValidPair, PointName = preprocessData(points, flows)
    Sizes = InitSize(InterData, PointNum)
    maxSize = max(Sizes)
    for i in range(0, PointNum):
        Sizes[i] = Sizes[i] / maxSize * 1000
    bestScoreResult = 0
    estSizeResult = []
    bestBeta = 0.1
    df_city = pd.DataFrame(index=PointName)
    df_socre = pd.DataFrame()
    for beta in range(1, 30, 1):
        bs, estSize = PSOSearch(InterData, PointNum, ValidPair, Sizes, float(beta / 10.0), 1000, 1000, 1, 2.0, 2.0)
        print('---- For beta %f, the best score is %f, at time %s ----'
              % (float(beta / 10.0), float(bs), str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))))
        df_socre[str(beta/10.0)] = [bs]
        df_city[str(beta/10.0)] = estSize
        # for bp in estSize:
        #     print(bp)
        if bs > bestScoreResult:
            bestScoreResult = bs
            bestBeta = float(beta / 10.0)
            estSizeResult = copy.deepcopy(estSize)

    result = [['beta', bestBeta]]
    for i in range(0, PointNum):
        result.append([PointName[i], estSizeResult[i]])
    df_city.to_csv("E:\\City Attractiveness\\Code\\city_scale.csv", header=True, index_label='city', encoding='gbk')
    df_socre.to_csv("E:\\City Attractiveness\\Code\\score.csv", header=True, index_label='score', encoding='gbk')
    return result


if __name__ == '__main__':
    points = []
    k = 0
    points_file = open("./points.txt", "r", encoding='utf-8')  # 文件格式编码为UTF-8无BOM格式（推荐），或者UTF-8格式
    # 但是UTF-8无BOM运行效率高，UTF-8格式运行效率很低
    for line in points_file.readlines():
        id, x, y = line.split('\t')
        points.append([id, float(x), float(y)])  # 添加 (id, x, y)
        k = k + 1
    points_file.close()

    flows = []
    flows_file = open("./flows.txt", "r", encoding='utf-8')  # 文件格式编码为UTF-8无BOM格式
    for line in flows_file.readlines():
        id1, id2, val = line.split('\t')
        flows.append([id1, id2, float(val)])  # 添加 (id1, id2, value)
    flows_file.close()

    res = gravityFit(points, flows)
    for r in res:
        print('%s   %f' % (r[0], r[1]))
