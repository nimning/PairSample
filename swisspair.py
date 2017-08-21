'''
A pairing algoirthm using swiss tournament algorithm for one round
'''
#time complexity: O(n^2.3) where n = 30 (30 images in each query)
import networkx as nx

try:
    import cPickle as pickle
except:
    import pickle as pickle

import csv
import random

class Tournament(object):
    def __init__(self, win_points = 3, draw_points = 1):
        #win_points: point get if  win
        #draw_points: point get if it is a draw
        #bye_points: point get if the player is not paired first time.
        self.win_points = 3
        self.draw_points = 1
        self.bye_points = win_points
        
        #palyers: Will hold all player data
        #'id' would be Murl Key. 'name' is the full name of the url
        '''
        id : { name:String,
               opponents:List, Each entry is a id number of someone you played
               results:List, Each entry is a list of (win, loss, draw) for the round
               points:Int, how many point this player gets so far}
        '''
        self.players = {}
        
        #Current round for the event
        self.current_round = 0

        #Pairings for the current round
        self.round_pairings = []

        #Contains lists of players sorted by the score they currently get in the event
        self.players_sortby_points = {}

        #Contains a list of points in the event from high to low
        self.points = []
        
        #check is this player has received a bye already
        self.already_bye = set()

    def add_player(self, id, name):
        self.players[id] = {"name": name,
                            "opponents":set(),
                            "results":[],
                            "points":0}
    
    #if this the first tournament, read files
    def load_players(self, path_to_load):
        with open(path_to_load) as players_file:
            player_reader = csv.reader(players_file, delimiter=',')
            for p in player_reader:
                #skip the row with headers
                if p[0] != 'ID:':
                    self.add_player( (p[0]), p[1] )         
    
    #load record
    def load_event(self, path_to_load):
        [self.current_round, self.players] = pickle.load(open(path_to_load, "rb" ) )
       
    #save the current event for the use of the next round
    def save_event(self, path_to_save):
        pickle.dump([self.current_round, self.players], open(path_to_save, "wb" ))

    #pair the players during this round
    def pair_round(self):
        """
            1.) Create a map 'players_sortby_points' whose key is 'score' and value is list of players with score 'score'
            2.) Create a list of all current points and sort them from highest to lowest
            3.) Loop through the 'players_sortby_points' and assign pairs between players having the same score
            and not paired before
            4.) Check for left over players and pairs the left over with the players in the next group.
            Make sure these left over players get paired first because they have higher scores.
            Note: step (3) and step (4) is implementd using the maximum-matching graph algorithm
        """
        
        self.current_round += 1
        self.round_pairings = []
        self.players_sortby_points = {}
        self.points = []
        
        #create 'players_sortby_points': group palyers by their score
        for player in self.players:
            info = self.players[player]

            #If this point has not accored
            if info['points'] not in self.players_sortby_points:
                self.players_sortby_points[info['points']] = []

            #Add player to the correct group
            self.players_sortby_points[info['points']].append(player)

        #crate 'points': all unique points of all current points and sort them from hight to low
        self.points.extend(self.players_sortby_points.keys())
        self.points.sort(reverse=True)
        #printdbg( "All points sorted from high to low: %s"%self.points, 3 )

        #Start paring the players.  
        for points in self.points:
            #Create the graph object for the group with same score
            graph = nx.Graph()
            #add palyers into the graph
            graph.add_nodes_from(self.players_sortby_points[points])

            #Create edges between all players in the graph who haven't already played with each other
            #If there are left overs in current group, we will pair them with the ones in the next group
            #Python does not have 'maximum matching', it only has 'maximal matching' and '
            #maximum weight matching' algorithm. So,I will use the maximum weight matching by assining 'weight'.
            #The player with score higher than group score is assinged with a high score to make sure it gets paired 
            #first
            for player in graph.nodes():
                for opponent in graph.nodes():
                    if opponent not in self.players[player]["opponents"] and player != opponent:
                        wgt = 1
                        if self.players[player]["points"] > int(points) or self.players[opponent]["points"] > int(points):
                            wgt = 10
                        #Create edge
                        graph.add_edge(player, opponent, weight=wgt)

            #pairing the players            
            pairings = nx.max_weight_matching(graph)

            #Pair the players. After pairing, remove them from the group, you do not need to repair again
            for p in pairings:
                if p in self.players_sortby_points[points]:
                    self.pair_players(p, pairings[p])
                    self.players_sortby_points[points].remove(p)
                    self.players_sortby_points[points].remove(pairings[p])

            #Check if we have palyer left out without pairing
            if len(self.players_sortby_points[points]) > 0:      
                #if these are the people left over after all pairing, it will be 
                #assigned to the next round and get a score.
                if self.points.index(points) + 1 == len(self.points):
                    while len(self.players_sortby_points[points]) > 0:
                        #If they are the last player give them a bye
                        self.assign_bye(self.players_sortby_points[points].pop())
                else:
                    #Add left-over players to the next point group down
                    next_points = self.points[self.points.index(points) + 1]
                    while len(self.players_sortby_points[points]) > 0:
                        self.players_sortby_points[next_points].append(self.players_sortby_points[points].pop())
        
        return self.round_pairings 
       
    
    def pair_players(self, p1, p2 ):
        self.players[p1]["opponents"].add(p2)
        self.players[p2]["opponents"].add(p1)
        self.round_pairings.append([p1, p2])

    def assign_bye(self, p1, reason="bye"):
        self.players[p1]["results"].append(1)
        self.players[p1]["opponents"].add("bye")
        
        #left over player receives a bye point if it has never received before
        if p1 not in self.already_bye:
            self.already_bye.add(p1)
            self.players[p1]["points"] += self.bye_points
    
    def report_match(self, results):
        #result is [p1, p2, game_result]
        for result in results:
            p1 = result[0]
            p2 = result[1]
            game_result = result[2]

            if game_result == 0:
                #If it is a draw
                self.players[p1]["points"] += self.draw_points
                self.players[p2]["points"] += self.draw_points
            #left win
            elif game_result == 1:
                self.players[p1]["points"] += self.win_points
            #right win
            else:
                self.players[p2]["points"] += self.win_points
            
            self.players[p1]["results"].append(game_result)
            self.players[p2]["results"].append(-1 * game_result)

    #get player-scors pair after the current round
    def players_points(self):
        players_points = []
        for id in self.players.keys():
            players_points.append([id, self.players[id]['points']])
        
        players_points.sort(reverse = True, key = lambda s:s[1])
        return players_points
            