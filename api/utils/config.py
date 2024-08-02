"""
Module containing utility functions for parsing configuration file.
"""

import yaml


def get_config():
	with open('config.yml', 'r') as file:
		config = yaml.safe_load(file)

	return config


# if __name__ == "__main__":
# 	refs = get_referrers()
# 	print(refs["referrers"])
	
