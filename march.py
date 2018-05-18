import regression

print "\nScript written assuming Python 2.7. If you experience errors, you may be running a different version or be missing the required packages."
print "Written by Phillip Brown (Lucky Phill) for the MRDA"
print "Contact: pbrown.mwerhun@gmail.com"
ranking = regression.Ranking(20170606,20180606,'june.csv',None,None,'disbanded.csv')
ranking.teams["Thunderquads Roller Derby Masculino"].min_games_required = 3
#ranking.teams["Atlanta Men's Roller Derby"].min_games_required = 4
ranking.create_ranking()
ranking.print_rankings()
for team in ranking.teams:
	ranking.plot_team(team)
# ranking2 = regression.Ranking(20170307,20180307,'march_clean.csv',None,'hiatus.csv','disbanded.csv')
# ranking2.create_ranking()
# ranking2.print_rankings()
# ranking.compare_rankings(ranking2)