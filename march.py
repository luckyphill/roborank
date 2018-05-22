import regression
import numpy as np

print "\nScript written assuming Python 2.7. If you experience errors, you may be running a different version or be missing the required packages."
print "Written by Phillip Brown (Lucky Phill) for the MRDA"
print "Contact: pbrown.mwerhun@gmail.com"
ranking = regression.Ranking(20170307,20180307,'march_clean.csv',None,None,'disbanded.csv')
ranking.teams["Thunderquads Roller Derby Masculino"].min_games_required = 3
ranking.create_ranking()
ranking.print_rankings(False)
ranking.expected_result('Manchester Roller Derby','Crash Test Brummies')
# for team in ranking.ranked_list_full:
# 	team.print_team()
#
improved_ranking = regression.ImprovedRanking(20170606,20180606,'clean_june_official.csv', 'ranking_dates.csv',None,None,'disbanded.csv')
improved_ranking.create_ranking()
improved_ranking.print_rankings(False)
improved_ranking.expected_result('Manchester Roller Derby','Crash Test Brummies')

reg_func = improved_ranking._make_regression_function(True)

x = np.zeros(len(improved_ranking.teams))

# # Manchester and Brummies
# x[35] = 533.1 #533.1
# x[53] = 533.1 #780.1

# # Fixed
# x[36] = 647.1 #647.1
# x[38] = 728.6 #728.6
# x[37] = 794.1 #794.1
# x[21] = 853.5 #853.5
# x[41] = 838.8 #838.8
# x[15] = 1000 #1000
# x[44] = 828.4 #828.4
# x[24] = 779.2 #779.2

# y = reg_func(x)
# print y[15], y[53]

# Only new
# -0.0187339159091 0.00933332751177

# All fixed teams
# -0.0187339159091 0.00933332751177