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
improved_ranking.expected_result('San Diego Aftershocks','Wheels of Mayhem')
