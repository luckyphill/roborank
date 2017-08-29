import csv
import sys
import operator
import copy
from scipy import log, cosh, tanh, exp, floor
import numpy as np
from fractions import Fraction
from scipy.optimize import bisect
import datetime as dt

day = dt.timedelta(1)

def str2dt(date_as_string):
	#expects date in the form YYYYMMDD
	#returns a datetime object
	date_as_int = int(date_as_string)
	year = date_as_int//10000
	month = (date_as_int - year*10000)//100
	day = date_as_int - year*10000 - month*100

	return dt.date(year, month, day)

def decay_function(game_date, window_start, window_end):
	diff = window_end - game_date
	months_ago = floor(12*diff.days/365)

	return (12-months_ago)/12
	# if window_end - game_date >180*day:
	# 	return 0.5
	# else:
	# 	return 1

class Team:
	def __init__(self, name):
		self.name = name
		self.power = None
		self.num_games = 0
		self.num_wins = 0
		self.is_new = False # a team will be considered new if it did not play last season
		self.min_games_required = 5
		self.min_unique_opponents = 3
		self.opponents = [] # a list of the teams they have played to track min requirements
		self.is_connected = False
		self.data_for_initial_power = []
		self.hiatus = False
		self.disbanded = False

	def increment_games(self):
		self.num_games += 1

	def increment_wins(self):
		self.num_wins +=1

	def is_active(self):
		if (self.num_games >= self.min_games_required) and (len(self.opponents) >= self.min_unique_opponents):
			return True
		else:
			return False

	def add_opponent(self, opponent):
		if (opponent not in self.opponents) and (opponent != self.name):
			self.opponents.append(opponent)

	def __str__(self):
		if self.power is None:
			return "     %s\nOpponents\n%s" %(self.name, str(self.opponents)) 
		else:
			return "%5.1f %s\nOpponents\n%s" %(self.power, self.name, str(self.opponents))

class Game:
	def __init__(self, game_data):
		#This class expects data directly from file so datetime conversion is needed
		self.date = str2dt(game_data[0])
		self.home_team = game_data[1]
		self.home_score = int(game_data[2])
		self.away_team = game_data[3]
		self.away_score = int(game_data[4])
		self.DOS = float(self.home_score-self.away_score)/float(self.home_score+self.away_score)

	def __str__(self):
		return "%s  %s  %3d  || %s  %3d" %(self.date, self.home_team.ljust(33), self.home_score, self.away_team.ljust(33), self.away_score)

class Week:
	#This class is only used internally and so dates will already be in datetime format 
	def __init__(self, start_date, end_date):
		self.start = start_date
		self.end = end_date
		self.games = []

	def add_game(self, game):
		self.games.append(game)

	def print_week(self):
		if self.games:
			#only prints the week if there are games in it
			print "\nWeek %s - %s" %(self.start, self.end)
			print "- "*48
			for game in self.games:
				print game

	def __str__(self):
		return "%s - %s\n" %(self.start, self.end)

class Ranking:
	def __init__(self, start_date, end_date):
		self.start = str2dt(start_date)
		self.end = str2dt(end_date)
		self.weeks = []
		self._make_weeks()
		self.games = []
		self.teams = {}
		self.connected_teams = []

	def _make_weeks(self):
		#weeks go from Thursday to Wednesday to make sure tournaments are captured in a single week
		wednesday = 2 #to match numerical weekday number in datetime
		num_days = (wednesday - self.start.weekday()) % 7
		last_day = self.start + num_days*day
		
		self.weeks.append(Week(self.start, last_day))
		last_day += 7*day
		while last_day <= self.end:
			self.weeks.append(Week(last_day - 6*day, last_day))
			last_day += 7*day

		if last_day != self.end:
			self.weeks.append(Week(last_day -6*day, self.end))

	def load_games(self, games_file):
		with open(games_file, 'rU') as csvfile:
			games_reader = csv.reader(csvfile, dialect='excel')
			for game in games_reader:
				self.games.append(Game(game))

		for game in self.games:
			for week in self.weeks:
				if week.start <= game.date <= week.end:
					week.add_game(game)

	def load_teams(self):
		#loads teams from given ranking period and fills in some key data
		for week in self.weeks:
			for game in week.games:
				home = game.home_team
				away = game.away_team
				#add teams if they don't already exist.
				#since this is for iterative method, set initial power as 700
				if home not in self.teams:
					self.teams[home] = Team(home)
					self.teams[home].power = 700

				if away not in self.teams:
					self.teams[away] = Team(away)
					self.teams[away].power = 700

				self.teams[home].increment_games()
				self.teams[away].increment_games()
				self.teams[home].add_opponent(away)
				self.teams[away].add_opponent(home)
				if game.home_score > game.away_score:
					self.teams[home].increment_wins()
				else:
					self.teams[away].increment_wins()

	def print_games_by_week(self):
		for week in self.weeks:
			week.print_week()

	def _calc_power_change(self, game, verbose_requested=False):
		scaling_factor = 100
		Kfactor = 30

		home = self.teams[game.home_team]
		away = self.teams[game.away_team]

		decay = decay_function(game.date,self.start,self.end)

		power_change = 0
		if home.is_new and not away.is_new:
			home.data_for_initial_power.append([away.power,-game.DOS]) # -ve need because of order of home and away
			if verbose_requested:
				print "%d  %s %s    %6.1f  || %s %6.1f   %6.1f   %6.3f" %(game.date, home.name.ljust(35), " "*6, power_change, away.name.ljust(35), away.power, -power_change, game.DOS)
				print "         " + home.name + " does not have a power rating from last season. Collecting data..."
			#collect data for calculating power rating home

		if away.is_new and not home.is_new:
			away.data_for_initial_power.append([home.power,game.DOS])
			if verbose_requested:
				print "%d  %s %6.1f    %6.1f  || %s %s   %6.1f   %6.3f" %(game.date, home.name.ljust(35), home.power, power_change, away.name.ljust(35), " "*6, -power_change, game.DOS)
				print "         " + away.name + " does not have a power rating from last season. Collecting data..."
			#collect data for calculating power rating away

		if home.is_new and away.is_new:
			if verbose_requested:
				print "%d  %s %s    %6.1f  || %s %s   %6.1f   %6.3f" %(game.date, home.name.ljust(35), " "*6, power_change, away.name.ljust(35), " "*6, -power_change,game.DOS)
				print "         " + home.name + " and " + away.name + " are both new. Special calculation method needed"
			# this case needs furhter investigation

		if not home.is_new and not away.is_new:
			predicted_DOS = -1 + 2/(1 + exp((away.power - home.power)/scaling_factor))
			power_change = Kfactor*(game.DOS - predicted_DOS)*decay
			if verbose_requested:
				print "%d  %s %6.1f    %6.1f  || %s %6.1f   %6.1f   %6.3f" %(game.date, home.name.ljust(35), home.power, power_change, away.name.ljust(35), away.power, -power_change, game.DOS)


		if home.is_new and len(home.data_for_initial_power) >= 3:
			reg_func = self.make_reg_function(home.data_for_initial_power)
			home.power = bisect(reg_func,0,2000)
			home.is_new = False
			if verbose_requested:
				print "         " + home.name + " has initial power rating %.1f"  %(home.power)

		if away.is_new and len(away.data_for_initial_power) >= 3:
			reg_func = self.make_reg_function(away.data_for_initial_power)
			away.power = bisect(reg_func,0,2000)
			away.is_new = False
			if verbose_requested:
				print "         " + away.name + " has initial power rating %.1f"  %(away.power)

		return power_change

	def _calc_weekly_change(self, week, verbose_requested=False):
		week_change = {}
		for game in week.games:
			if game.home_team not in week_change:
				week_change[game.home_team] = 0
			if game.away_team not in week_change:
				week_change[game.away_team] = 0

			power_change = self._calc_power_change(game,verbose_requested)
			week_change[game.home_team] += power_change
			week_change[game.away_team] -= power_change

		for team, change in week_change.iteritems():
			if not self.teams[team].is_new:
				self.teams[team].power += change

	def _update_powers(self, verbose_requested=False):
		if verbose_requested:
			print "\nPower rating changes"
			print "%s      %s  %s   %s || %s  %s  %s    %s" %("Date", "Home Team".ljust(33), "  Power  ", "Change", "Away Team".ljust(33),"  Power  ", "Change","DOS")
			print "%s" %("- "*65)

		for week in self.weeks:
			if week.games:
				if verbose_requested:
					print "\nPower rating changes for the week %d - %d" %(week.start, week.end)
					print "-"*53
				self._calc_weekly_change(week, verbose_requested)

	def calc_iterative_ranking(self):
		indicator_team = self.teams.keys()[3]
		prev_power = 1 # ensures it enters the while loop at least once
		while abs(self.teams[indicator_team].power - prev_power) > .001:
			prev_power = copy.copy(self.teams[indicator_team].power)
			self._update_powers(False)

		# find the team with the most unique opponents
		most_connected_team = self.teams.values()[0]
		for team in self.teams.values():
			if len(team.opponents) > len(most_connected_team.opponents):
				most_connected_team = team

		self.determine_connectivity(most_connected_team)

	def print_rankings(self, only_active_teams=False):
		print "\nRankings for period %s to %s" %(self.start, self.end)
		if only_active_teams:
			print "Only teams active this season are shown"
		print "Rank   Power  Games   Team"

		unrankable = []
		inactive = []
		no_games = []
		hiatus = []
		disbanded = []
		disconnected = []

		rankings = sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)
		counter = 1

		for team in rankings:
			if team[1].power is None: #makes sure the team has a power rating first
				unrankable.append(team[0])
			elif team[1].hiatus:
				hiatus.append(team[0])
			elif team[1].disbanded:
				disbanded.append(team[0])
			elif not team[1].is_connected:
				disconnected.append(team[0])
			else:
				if only_active_teams:
					if team[1].is_active():
						print "%3d   %6.1f    %2d    %s" %(counter, team[1].power, team[1].num_games, team[1].name)
						counter += 1
					else:
						if team[1].num_games == 0:
							no_games.append(team[0])
						else:
							inactive.append(team[0])
				else:
					print "%3d   %6.1f    %2d    %s" %(counter, team[1].power, team[1].num_games, team[1].name)
					counter += 1
				

		if unrankable:
			print "\nThe following teams are currenty unrankable because no power has been assigned"
			for team in unrankable:
				print team

		if inactive:
			print "\nThe following teams played games, but did not meet minimum activity requirements"
			for team in inactive:
				print team

		if no_games:
			print "\nThe following teams played no games in the given period"
			for team in no_games:
				print team

		if hiatus:
			print "\nThe following teams are on hiatus"
			for team in hiatus:
				print team

		if disbanded:
			print "\nThe following teams have disbanded"
			for team in disbanded:
				print team

		if disconnected:
			print "\nThe following teams are disconnected from the main group"
			for team in disconnected:
				print team

	def determine_connectivity(self, team):
		# used to check if teams are connected to the main group (North America) for the sake of the iterative method
		# choose a team to be the root node - the winner of champs or the team with the most unique opponents would be suitable choices
		# make this recursive and initial pass in is root node
		team.is_connected = True
		for opponent in team.opponents:
			if opponent not in self.connected_teams:
				self.connected_teams.append(opponent)
				self.determine_connectivity(self.teams[opponent])

ranking = Ranking(20160630,20170630)
ranking.load_games('../Data/MRDAallgames.csv')
ranking.load_teams()
hiatus_leagues = ["Big O","Slaughter Squad", "Quads of War", "Death Quads", "Quadfathers", "Your Mom", "Mean Mountain"]
disbanded_leagues = ["Rattleskates", "Jersey Boys", "Tulsa Derby Militia", "Bomberz"]
for team in hiatus_leagues:
	if team in ranking.teams:
		ranking.teams[team].hiatus = True

for team in disbanded_leagues:
	if team in ranking.teams:
		ranking.teams[team].disbanded = True
# ranking.teams["ThunderQuads"].min_games_required=3
# ranking.teams["Victoria Men's Roller Derby"].min_games_required=3
# ranking.teams["Sydney City SMASH"].min_games_required=3
# ranking.teams["Carnage"].min_games_required=3
# ranking.teams["Scartel"].min_games_required=3
ranking.print_games_by_week()
ranking.calc_iterative_ranking()
ranking.print_rankings(False)

diff_list =[]
win_score_list =[]
lose_score_list = []
for game in ranking.games:
	diff = abs(game.home_score-game.away_score)
	diff_list.append(diff)
	if diff<20:
		if game.home_score>game.away_score:
			win_score_list.append(game.home_score)
			lose_score_list.append(game.away_score)
		else:
			win_score_list.append(game.away_score)
			lose_score_list.append(game.home_score)

w_avg = np.mean(win_score_list)
w_std = np.std(win_score_list)
w_maxsc = max(win_score_list)
w_minsc = min(win_score_list)
w_perc1 = np.percentile(win_score_list,1)
w_perc99 = np.percentile(win_score_list,99)
print w_avg, w_std, w_maxsc, w_minsc, w_perc1, w_perc99

l_avg = np.mean(lose_score_list)
l_std = np.std(lose_score_list)
l_maxsc = max(lose_score_list)
l_minsc = min(lose_score_list)
l_perc1 = np.percentile(lose_score_list,1)
l_perc99 = np.percentile(lose_score_list,99)
print l_avg, l_std, l_maxsc, l_minsc,l_perc1, l_perc99


#print np.histogram(diff_list, bins="fd")