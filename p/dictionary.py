# # # # # # # # # # # # # # #                             # dictionary
# # # # # # # # # # # # # # # students={1:"Ram", 2:"Jayul", 3:"Rahul",4:"Anjali",5:"Riya"}

# # # # # # # # # # # # # # # marks={1:22,2:33,3:16,4:39,5:45}

# # # # # # # # # # # # # # # print(students)
# # # # # # # # # # # # # # # print(marks)
# # # # # # # # # # # # # # #                         check if dublicate

# # # # # # # # # # # # # # marks={1:22,2:33,3:16,4:39,5:45,4:45, 4:55}

# # # # # # # # # # # # # # print(marks)
# # # # # # # # # # # # #                            
# # # # # # # # # # # # # 
# # # # # # # # # # # #                                 dictionary 3 print students
# # # # # # # # # # # # students={} 
# # # # # # # # # # # # students[1]="Ram"
# # # # # # # # # # # # students[22]="Jayul"
# # # # # # # # # # # # students[3]="Rahul"
# # # # # # # # # # # # students[44]="Anjali"

# # # # # # # # # # # # print(students)
# # # # # # # # # # #                           dictionary 4  print studentname and number

# # # # # # # # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya"}

# # # # # # # # # # # print(students[22])

# # # # # # # # # # # print(students.get(44))
# # # # # # # # # #                             # dictionary 6 
# # # # # # # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}

# # # # # # # # # # for key,value in students.items():
# # # # # # # # # #     print(key,value)
# # # # # # # # #                             # dictionary 7 key in student
# # # # # # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}

# # # # # # # # # for key in students:
# # # # # # # # #     print(key)
# # # # # # # #                                         # dictionary 8

# # # # # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}

# # # # # # # # for key in students:
# # # # # # # #     print(students[key])

# # # # # # #                                     # dictionary 9

# # # # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}

# # # # # # # for value in students.values():
# # # # # # #     print(value)

# # # # # #                                         # dictionary 10

# # # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}

# # # # # # keys = students.keys()
# # # # # # values = students.values()

# # # # # # print(keys)
# # # # # # print(values)

# # # #                             #  dictionary 10 student name and number print both


# # # # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}

# # # # # keys = students.keys()
# # # # # values = students.values()

# # # # # print(keys)
# # # # # print(values) 
# # # #                             dictionary 11
# # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}
# # # students.pop(22)
# # # print(students)
# # # students.popitem()
# # # print(students,"popitem")
# # # del students[44]
# # # print(students)
# # # students.clear() 
# # # print(students) 

# #                             # dictionary 12 delete item 

# # # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya",12:"Hiral",33:"Karan"}
# # # students.pop(22)
# # # print(students)
# # # students.popitem()
# # # print(students)
# # # del students[44]
# # # print(students)
# # # students.clear()
# # # print(students)
                           
# #                         # dictionary 13 how to addd 

# # students={1:"Ram", 22:"Jayul", 3:"Rahul",44:"Anjali",50:"Riya"}
# # print(students)

# # students[33]="Hiral"
# # print(students)

#                             # dictionary 14 how to merege 
# cubes={1: 1, 2: 8, 3: 27}
# cubes1={4:64, 5:125}

# cubes.update(cubes1)

# print(cubes)
