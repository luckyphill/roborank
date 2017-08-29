# a object oriented approach to the ranking system

import csv
import operator
import copy
from scipy import log, cosh, tanh, exp
from fractions import Fraction
from scipy.optimize import bisect

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
		self.date = int(game_data[0])
		self.home_team = game_data[1]
		self.home_score = int(game_data[2])
		self.away_team = game_data[3]
		self.away_score = int(game_data[4])
		self.DOS = float(self.home_score-self.away_score)/float(self.home_score+self.away_score)

	def __str__(self):
		return "%d  %s  %3d  || %s  %3d" %(self.date, self.home_team.ljust(33), self.home_score, self.away_team.ljust(33), self.away_score)

class Week:
	def __init__(self, start_date, end_date):
		self.start = start_date
		self.end = end_date
		self.games = []

	def add_game(self, game):
		self.games.append(game)

	def print_week(self):
		if self.games:
			print "\nWeek %d - %d" %(self.start, self.end)
			print "- "*46
			for game in self.games:
				print game

	def __str__(self):
		return "%d - %d\n" %(self.start, self.end)

class Season:
	def __init__(self, year):
		self.year = year
		self.weeks = []
		self._make_calender()
		self.games = []
		self.teams = {}
		self.connected_teams = [] # a list of teams that are part of the 'main group'

	def _make_calender(self):
		# the goal of this function is to produce a list of Week objects that start on a Thursday and end on a Wednesday
		# yeah, I know, there's a datetime object, but this matches the date format in the database
		self._date_list = []
		date = self.year*10000 + 101 # start year at 1st Jan
		month_lengths = [31,28,31,30,31,30,31,31,30,31,30,31]
		if self.year %4 == 0: #leap years
			month_lengths[1]=29
		
		for length, month in zip(month_lengths, xrange(1,13)):
			for i in xrange(1,length+1):
				self._date_list.append(self.year*10000 + month*100 + i)

		referenceThursday = 20090101 #2009 started with a Thursday and is immediately after a leap year
		num_leap_years = int((self.year - 2009)//4) 
		num_common_years = self.year - 2009 - num_leap_years
		starting_day = (num_leap_years*366 + num_common_years*365)%7 #if 0 then starts Thursday, 1 starts Friday etc.
		self._first_Thursday = self.year*10000 +101 + (7-starting_day)

		if self._first_Thursday == self._date_list[0]:
			#if the year starts on Thursday
			self.weeks.append(Week(self._first_Thursday,self._date_list[6]))
		else:
			#if the year does not start on Thursday
			self.weeks.append(Week(self._date_list[0],self._first_Thursday-1))

		start_index = self._date_list.index(self.weeks[0].end)+1
		self.weeks.extend([Week(self._date_list[i],self._date_list[i+6]) for i in xrange(start_index,len(self._date_list)-6,7)])
		
		# if the year doesn't end on a Wednesday
		if self.weeks[-1].end != self._date_list[-1]:
			self.weeks.append(Week(self.weeks[-1].end+1,self._date_list[-1]))

	def load_games(self, games_file):
		with open(games_file, 'rU') as csvfile:
			games_reader = csv.reader(csvfile, dialect='excel')
			for game in games_reader:
				self.games.append(Game(game))

		for game in self.games:
			for week in self.weeks:
				if week.start <= game.date <= week.end:
					week.add_game(game)

	def load_seeded_teams(self, seed_teams):
		# use this to load seed data from previous season
		for team in seed_teams:
			self.teams[team] = Team(team)
			if seed_teams[team].is_connected:
				# copies over the seed power only if the team has a connection to the main group
				self.teams[team].power = copy.copy(seed_teams[team].power)
			else:
				# if the team is not connected, then temporarily treating it as new
				self.teams[team].is_new = True
				print self.teams[team].name + " is not connected to the main region so can't be ranked globally"

	def load_teams_for_seeding(self):
		#use this to load teams for iterative method
		# if using immediately after a previous season, need to remove teams with no games
		for team in self.teams.values():
			if team.num_games == 0:
				del self.teams[team.name]

		for game in self.games:
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

	def current_ranking(self, verbose_requested=False):
		self._update_powers(verbose_requested)
		#runs the algorithm on the current years games

	def seed_ranking_for_next_year(self, verbose_requested=False):
		indicator_team = self.teams.keys()[3]
		prev_power = 1 # ensures it enters the while loop at least once
		while abs(self.teams[indicator_team].power - prev_power) > .001:
			prev_power = copy.copy(self.teams[indicator_team].power)
			self._update_powers(verbose_requested)

		# find the team with the most unique opponents
		most_connected_team = self.teams.values()[0]
		for team in self.teams.values():
			if len(team.opponents) > len(most_connected_team.opponents):
				most_connected_team = team

		self.determine_connectivity(most_connected_team)

	def _calc_power_change(self, game, verbose_requested=False):
		scaling_factor = 100
		Kfactor = 30

		if game.home_team not in self.teams:
			self.add_new_team(game.home_team)
		if game.away_team not in self.teams:
			self.add_new_team(game.away_team)

		home = self.teams[game.home_team]
		away = self.teams[game.away_team]

		home.add_opponent(away.name)
		away.add_opponent(home.name)

		home.increment_games()
		away.increment_games()

		if game.home_score > game.away_score:
			home.increment_wins()
		else:
			away.increment_wins() # no draws in derby

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
			power_change = Kfactor*(game.DOS - predicted_DOS)
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

	def print_games_by_week(self):
		for week in self.weeks:
			week.print_week()

	def print_rankings(self, only_active_teams):
		print "\nRankings for Season %d" %(self.year)
		if only_active_teams:
			print "Only teams active this season are shown"

		unrankable = []
		inactive = []
		no_games = []

		rankings = sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)
		counter = 1

		for team in rankings:
			if team[1].power is None: #makes sure the team has a power rating first
				unrankable.append(team[0])
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
			print "\nThe following teams played no games this season and will not be ranked next season"
			for team in no_games:
				print team

	def add_new_team(self,team):
		self.teams[team] = Team(team)
		self.teams[team].is_new = True

	def make_reg_function(self, teamData):
		# opposing team powers and DOS for each of the first three games a new team has played
		P1 = teamData[0][0]
		DOS1 = teamData[0][1]
		P2 = teamData[1][0]
		DOS2 = teamData[1][1]
		P3 = teamData[2][0]
		DOS3 = teamData[2][1]
		# this is ugly. there really is no clean way to do it
		# creates the least squares function that needs to be minimised
		def reg_function(x):
			return -(tanh((x-P1)/200)+DOS1)/cosh((x-P1)/200)**2-(tanh((x-P2)/200)+DOS2)/cosh((x-P2)/200)**2-(tanh((x-P3)/200)+DOS3)/cosh((x-P3)/200)**2
		return reg_function

	def determine_connectivity(self, team):
		# used to check if teams are connected to the main group (North America) for the sake of the iterative method
		# choose a team to be the root node - the winner of champs or the team with the most unique opponents would be suitable choices
		# make this recursive and initial pass in is root node
		team.is_connected = True
		for opponent in team.opponents:
			if opponent not in self.connected_teams:
				self.connected_teams.append(opponent)
				self.determine_connectivity(self.teams[opponent])

#boolean static variables for printing rankings
only_active_teams = True
all_teams = False
verbose = True
quiet = False

# do this to get the iterative initial power ratings from last season
season2015 = Season(2015)
season2015.load_games('../Data/MRDA2015games.csv')
season2015.load_teams_for_seeding()
season2015.seed_ranking_for_next_year() #seed ranking is iterative, verbose is a BAD idea
#season2015.print_rankings(all_teams)

season2016 = Season(2016)
season2016.load_games('../Data/MRDA2016games2.csv')
season2016.load_seeded_teams(season2015.teams)
season2016.current_ranking(verbose)
season2016.print_rankings(only_active_teams)

season2016.load_teams_for_seeding()
season2016.seed_ranking_for_next_year()
season2016.print_rankings(all_teams)

# #if a team is not connected from previous season, it is currently treated as a new team in load_seeded_teams

season2017 = Season(2017)
season2017.load_games('../Data/MRDA2017games2.csv')
season2017.load_seeded_teams(season2016.teams)
season2017.current_ranking(verbose)
season2017.print_rankings(all_teams)
