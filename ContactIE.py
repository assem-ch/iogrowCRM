"""
A script to inport and export contact info into vcf, vcard, csv, excel, files, 
text files

dependencies: pyvcf, xlrd


Supported types:
implemented => iogrow_csv, txt
unimplemented =>

"""

import vcf,  xlrd, csv


class Contact:
    def __init__(self,
                 given_name = '',
                 family_name= '',
                 display_name = '',
                 title = "",
                 emails = [""],
                 organization="",
                 phone = "",
                 fax = "",
                 url = "",
                 address = ""
                  ):

        ## init values
        self.given_name = given_name
        self.family_name = family_name
        self.display_name = display_name
        self.title = title
        self.emails = emails
        self.organization = organization
        self.phone = phone
        self.fax = fax
        self.url = url
        self.address = address

    def __repr__(self):
        return self.given_name + " " + self.family_name + "(" + self.display_name + ")"
    
    def __str__(self):
        string = "[Contact : %s ]" % self.display_name + "\n"
        string += "Given Name: " + self.given_name + "\n"
        string += "Family Name: " + self.family_name + "\n"
        string += "Display Name: " + self.display_name + "\n"
        string += "Title: " + self.title  + "\n"

        string += "Emails: " + ",".join(self.emails) + "\n"
        string += "Organization: " + self.organization + "\n"
        string += "Phone: " + self.given_name + "\n"
        string += "Fax: " + self.fax + "\n"
        string += "Fax: " + self.fax + "\n"
        string += "Url: " + self.url + "\n"
        string += "Address: " + self.address + "\n"

        return string

    def importer(self, file_type, file_path):
        """
        types: vcf, txt, exls, iogrow_csv, evolution_csv, mozilla_csv, outlook_csv 
        """
        f = open(file_path, "rb")
        if file_type == "iogrow_csv":
            csvreader = csv.reader(f, delimiter=';')
            for row in csvreader:
                self.given_name = row[0]
                self.family_name = row[1]
                self.display_name = row[2]
                self.title = row[3]
                self.emails = row[4]
                self.organization = row[5]
                self.phone = row[6]
                self.fax = row[7]
                self.url = row[8]
                self.address = row[9]
        
        f.close()

    def exporter(self, file_type, file_path):
        """
        types: vcf, txt, exls,  iogrow_csv, evolution_csv, mozilla_csv, outlook_csv , pdf
        """
        f = open(file_path, "w")
        if file_type == "iogrow_csv":
            csvwriter = csv.writer(f, delimiter=';')
            csvwriter.writerow([
                                "given_name",
                                "family_name",
                                "display_name",
                                "title",
                                "email",
                                "organization",
                                "phone",
                                "fax",
                                "url",
                                "address"
                                ]
                                )
            csvwriter.writerow(
                               [
                                  self.given_name,
                                  self.family_name,
                                  self.display_name,
                                  self.title,
                                  self.emails[0],
                                  self.organization,
                                  self.phone,
                                  self.fax,
                                  self.url,
                                  self.address
                                ])
        elif file_type == "txt":
            f.write(str(self))

        f.close()


if __name__ ==  "__main__":
    contact = Contact(
                         given_name = 'Assem',
                         family_name= 'Chelli',
                         display_name = 'BigO',
                         title = "Engineer",
                         emails = ["assem.ch@gmail.com"],
                         organization= "iogrow",
                         phone = "00213794243270",
                         fax = "00213794243270",
                         url = "00213794243270",
                         address = "Cite 23 logs bt 4 n6 Taher"
                          )
    print repr(contact)
    print str(contact)
    contact.exporter("iogrow_csv","contact.csv")
    contact2 = Contact()
    contact2.importer("iogrow_csv","contact.csv")
    print str(contact)
