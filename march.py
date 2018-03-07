import regression

print "\nScript written assuming Python 2.7. If you experience errors, you may be running a different version or be missing the required packages."
print "Written by Phillip Brown (Lucky Phill) for the MRDA"
print "Contact: pbrown.mwerhun@gmail.com"
ranking = regression.Ranking(20170307,20180307,'march_clean.csv','hiatus.csv','disbanded.csv')
ranking.teams["Thunderquads Roller Derby Masculino"].min_games_required = 3
ranking.teams["Atlanta Men's Roller Derby"].min_games_required = 4
ranking.regression_ranking()
ranking.anchor_regions(False)
ranking.print_rankings(True)
#ranking.print_games_by_week()
ranking.expected_result("Thunderquads Roller Derby Masculino","Victoria Men's Roller Derby")
ranking.plot_team("Thunderquads Roller Derby Masculino")
ranking.plot_team("Victoria Men's Roller Derby")
