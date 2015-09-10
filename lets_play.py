from lxml import html
import requests,json,httplib,urllib,time

applicationId = "UnWG5wrHS2fIl7xpzxHqStks4ei4sc6p0plxUOGv"
apiKey = "g7Cj2NeORxfnKRXCHVv3ZcxxjRNpPU1RVuUxX19b"

#
# Adds the team data for a given teamId.
# This method is called from teamListUpdate()
#
def teamUpdate(id):
  print id
  connection = httplib.HTTPSConnection('api.parse.com', 443, timeout=60)
  connection.connect()
  retries = 0
  while True:
    try:
      teamPage = requests.get('http://www.letsplaysoccer.com/facilities/12/teams/%s' % id)
      tree = html.fromstring(teamPage.text)
      divisionHeader = tree.xpath("//*[@id='mainright']/h3")
      divisionHeader = divisionHeader[0].text.rstrip()
      divisionArray = divisionHeader.split(' ')
      if len(divisionArray) < 7:
        division = divisionArray[5]
      else: 
        division = divisionArray[5] + divisionArray[6]

      season = divisionArray[1]

      params = urllib.urlencode({"where":json.dumps({
        "teamId": id})})
      connection.request('GET', '/1/classes/Teams?%s' % params,'', {
             "X-Parse-Application-Id": applicationId,
             "X-Parse-REST-API-Key": apiKey,
           })
      results = json.loads(connection.getresponse().read())
      # Object doesn't exist, POST to create new.	

      if results.values() == [[]]:
         call = 'POST'
         objId = ''
      # Object exists, PUT to update existing.
      else: 
         call = 'PUT'
         # Better way to obtain objectID for update?  (nested dictionary/array/dictionary is ugly!  Stupid Python...)
         objId = '/%s' % results['results'][0]['objectId']

      connection.request(call, '/1/classes/Teams%s' % objId, json.dumps({
                   "teamId": id,
                   "name": tree.xpath("//*[@id='mainright']/h1")[0].text.rstrip(),
                   "division": division,
                   "season": season
                 }), {
                   "X-Parse-Application-Id": applicationId,
                   "X-Parse-REST-API-Key": apiKey,
                   "Content-Type": "application/json"
                 })
      results = json.loads(connection.getresponse().read())
      print results
    except Exception, e:
      print str(e)   
      retries += 1
      if retries < 5:
        print "Error retry %s..." % retries
        time.sleep(5)
        connection = httplib.HTTPSConnection('api.parse.com', 443, timeout=60)
        connection.connect()
        continue
      else:
        print "There was a failure in teamListUpdate(), could not resolve after 5 attempts, aborting..."
        return
    break

#
# To be run before 'fullGameListUpdate()' to seed iterable data.
# Scrapes the Let's Play site to obtain a list of all teams in (currently) facility 12 and stores the team data in the 'Teams' table of the Parse DB.
#
def teamListUpdate():
  page = requests.get('http://www.letsplaysoccer.com/facilities/12/teams')
  tree = html.fromstring(page.text)
  # array of teams
  teamNames = tree.xpath("//a[contains(@href, '/facilities/12/teams/' )]")
  for team in teamNames:
    teamUpdate(team.attrib['href'].split('/')[-1])

#
# To be run AFTER 'teamListUpdate()'
# Given a teamId, scrapes the Let's Play site for that teamId and stores a list of all games played by the corresponding team in the 'Games' table of the Parse DB.
#
# teamId : Corresponds to the teamId that the team is referenced in the Let's Play href to view team data.
#
def gamesUpdate(teamId):
  print teamId
  connection = httplib.HTTPSConnection('api.parse.com', 443, timeout=60)
  connection.connect()
  page = requests.get('http://www.letsplaysoccer.com/facilities/12/teams/%s' % teamId)
  tree = html.fromstring(page.text)
  # array of teams
  games = tree.xpath("//tr[td]")
  for game in games:
    retries = 0
    while True:
      try:
        children = game.getchildren()
        if len(children) != 7:
          date = children[0].getchildren()[0].text
          field = children[1].text.strip()
          homeTeam = children[2].getchildren()[0]
          awayTeam = children[3].getchildren()[0]
          
          awayTeam = awayTeam.attrib['href'].split('/')[-1]
          homeTeam = homeTeam.attrib['href'].split('/')[-1]

          # Add Team information for HomeTeam if it doesn't exist in the table.
          params = urllib.urlencode({"where":json.dumps({
                "teamId": homeTeam
          })})
          connection.request('GET', '/1/classes/Teams?%s' % params,'', {
                 "X-Parse-Application-Id": applicationId,
                 "X-Parse-REST-API-Key": apiKey,
               })
          results = json.loads(connection.getresponse().read())
          # Object doesn't exist, POST to create new.
          if results.values() == [[]]:
	    print "ADDING TEAM THAT DID NOT EXIST AND ADDING THEIR GAME LIST!"
	    teamUpdate(homeTeam)
            gamesUpdate(homeTeam)

          # Add Team information for AwayTeam if it doesn't exist in the table.
          params = urllib.urlencode({"where":json.dumps({
                "teamId": awayTeam
          })})
          connection.request('GET', '/1/classes/Teams?%s' % params,'', {
                 "X-Parse-Application-Id": applicationId,
                 "X-Parse-REST-API-Key": apiKey,
               })
          results = json.loads(connection.getresponse().read())
          # Object doesn't exist, POST to create new.
          if results.values() == [[]]:
            print "ADDING TEAM THAT DID NOT EXIST AND ADDING THEIR GAME LIST!"
            teamUpdate(awayTeam)
            gamesUpdate(awayTeam)

          score = "".join(children[4].text.split()).split("-") 
          if score[0]:
            homeTeamScore = score[0]
            awayTeamScore = score[1]
          else:
            homeTeamScore = ""
            awayTeamScore = ""

          params = urllib.urlencode({"where":json.dumps({
            "date": date,
            "field": field,
            "homeTeam": homeTeam,
            "awayTeam": awayTeam})})
          connection.request('GET', '/1/classes/Games?%s' % params,'', {
                 "X-Parse-Application-Id": applicationId,
                 "X-Parse-REST-API-Key": apiKey,
               })
          results = json.loads(connection.getresponse().read())

          # Object doesn't exist, POST to create new.
          if results.values() == [[]]:
             call = 'POST'
             objId = ''
          # Match exists, PUT to update existing match.
          else:
             call = 'PUT'
             objId = '/%s' % results['results'][0]['objectId']

          connection.request(call, '/1/classes/Games%s' % objId, json.dumps({
                       "date": date,
                       "field": field,
                       "homeTeam": homeTeam,
                       "awayTeam": awayTeam,
                       "homeTeamScore": homeTeamScore,
                       "awayTeamScore": awayTeamScore
                     }), {
                       "X-Parse-Application-Id": applicationId,
                       "X-Parse-REST-API-Key": apiKey,
                       "Content-Type": "application/json"
                     })
          results = json.loads(connection.getresponse().read())
          print results
        else:
          print"\n\n\n\Standings\n"
      except Exception, e:
        print str(e)
        retries += 1
        if retries < 5:
	  print "Error retry %s..." % retries
          time.sleep(5)
          connection = httplib.HTTPSConnection('api.parse.com', 443, timeout=60)
          connection.connect()
          continue
        else:
          print "There was a failure in gameUpdate(), could not resolve after 5 attempts, aborting..."
          return
      break

#
# To be run AFTER 'teamListUpdate()'
# Iterates across all teams stores in the 'Teams' table of the Parse DB and updates the 'Games' table according to the team's schedule.
#
def fullGameListUpdate():
  # WARNING: Parse has a soft limit of 100 items per query.  This can be overwritten to a maximum of 1000.  In the immediate term this does not matter, but we will need to 
  #  be prepared to handle this if we grow above 1000 items.
  params = urllib.urlencode({"limit":1000})
  connection = httplib.HTTPSConnection('api.parse.com', 443)
  connection.connect()
  connection.request('GET', '/1/classes/Teams?%s' % params, '', {
         "X-Parse-Application-Id": applicationId,
         "X-Parse-REST-API-Key": apiKey,
       })
  results = json.loads(connection.getresponse().read())
  teams = results['results']
  for team in teams:
    gamesUpdate(team['teamId'])

hours=10

teamListUpdate()
fullGameListUpdate()

#while True:
#  print "Running at: %s" % time.ctime()
#  teamListUpdate()
#  #gamesUpdate()
#  fullGameListUpdate()
#  print "Finished run at: %s" % time.ctime()
#  time.sleep(hours*60*60)