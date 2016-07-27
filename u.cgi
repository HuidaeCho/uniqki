#!/usr/bin/env perl
################################################################################
# Uniqki:	Unique Wiki <http://uniqki.isnew.info>
# Author:	Huidae Cho
# Since:	May 23, 2007
#
# Copyright (C) 2007, 2008, 2010, 2011, 2016 Huidae Cho <http://geni.isnew.info>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
################################################################################

# The document root directory relative to the server's URL including /~user, if
# any.  For example, if the full URL path to index.html is
# http://foo.bar.net/~user/index.html, $doc_root should be set to ".".  Leave
# it blank if you can run u.cgi outside of the cgi-bin directory.
my $doc_root = "";

# Temporary admin ID: admin, password: admin.  DO NOT CHANGE THIS VARIABLE.
my $tmp_adminpw = 'admin:wpmTmn6p2d18b7b0f03e204f1321983cfe7fd6cd53d78765:admin:@:';
# Running u.cgi for the first time will create the password file u.pw using the
# $adminpw credential, which is set to $temporary_adminpw by default.  Since
# this password is public, make sure to change the admin password after the
# first login to update the password file.  If $adminpw in the following line
# is not the same as $temporary_adminpw, u.cgi will assume that you have
# changed $adminpw to remove the password file and use u.cgi instead for login,
# and will not create the password file anymore.  Using this feature, it is
# possible to operate a Uniqki site with the u.cgi file alone by removing the
# password file after setting the $adminpw variable to your new credential in
# u.pw.  Make sure to back up this variable when updating the u.cgi script.
# Optionally, you can create u.cfg and template files in u.tpl by running
# u.cgi?config and u.cgi?template, respectively, but these files are only used
# for customizations and are not required.
my $adminpw = $tmp_adminpw;

################################################################################
use strict;
use vars qw(
	$U_CGI $HTTP_BASE $DOC_BASE

	$HOSTING

	$HTTP_COOKIE $HTTP_HOST $SERVER_NAME $SCRIPT_NAME $PATH_INFO
	$QUERY_STRING $REQUEST_METHOD $CONTENT_LENGTH

	$USER $ADMIN $PAGE $FILE $VERSION $TITLE $TEXT $PREVIEW $TIME
	%MESSAGES $MESSAGE

	$RSS_TITLE $RSS_DESCRIPTION
	$TIME_ZONE $PW $TPL $CSS $MSG $CHARSET
	$INACTIVE_TIMEOUT $SET_PASSWORD_TIMEOUT $RESET_PASSWORD_TIMEOUT
	$EMAIL_ADDRESS $PAGE_NAME_STYLE

	$READ_ACCESS $WRITE_ACCESS

	$HEADER $FOOTER
	$WIKI_HEADER $WIKI_FOOTER $WIKI_NEW_PAGE $WIKI_UPLOAD

	$wiki $begin_parsing $parse_line $end_parsing

	$text $protocol $protocol_char $protocol_punct $image_ext $block
	$re_i_start $re_i @re @re_sub $toc $notoc %h_i $h_top $h_prev $p
	$li_i @li @li_attr $pre $table
);

umask 022;

if(!defined $ENV{GATEWAY_INTERFACE}){
	print "Please run this script from a web browser!\n";
	printf "my \$tmp_adminpw = 'admin:%s:admin:\@:';\n", hash_password("admin", "admin");
	exit;
}

################################################################################
# CGI variables
$HTTP_COOKIE = $ENV{HTTP_COOKIE};
$HTTP_HOST = $ENV{HTTP_HOST};
$SERVER_NAME = $ENV{SERVER_NAME};
$SCRIPT_NAME = $ENV{SCRIPT_NAME};
$PATH_INFO = $ENV{PATH_INFO};
$QUERY_STRING = $ENV{QUERY_STRING};
$REQUEST_METHOD = $ENV{REQUEST_METHOD};
$CONTENT_LENGTH = $ENV{CONTENT_LENGTH};

################################################################################
# Useful variables
$U_CGI = $SCRIPT_NAME;
$HTTP_BASE = "http://$HTTP_HOST";
$DOC_BASE = "$HTTP_BASE$U_CGI"; $DOC_BASE =~ s#/[^/]*$##;
$PAGE = substr $PATH_INFO, 1; $PAGE =~ s#/.*$##;
$PAGE =~ s#\.(?:html|txt|txt\.v)$##;
$FILE = $PATH_INFO; $FILE =~ s#^/[^/]+##; $FILE =~ s#^/##;

################################################################################
# Awardspace.com free web hosting
$HOSTING = "";
if(-d "/home/www/$SERVER_NAME"){
	$HOSTING = "awardspace";
	$_ = "/home/www/$SERVER_NAME$SCRIPT_NAME";
	s#/[^/]*$##;
	chdir $_;
}
if($doc_root eq ""){
	$U_CGI =~ s#^.*/##;
}else{
	($_ = $U_CGI) =~ s#/[^/]+$##;
	s#^/~[^/]+##;
	if($_ eq ""){
		chdir $doc_root;
	}else{
		s#^/##; s#[^/]+#..#g;
		chdir "$_/$doc_root";
	}
	$DOC_BASE = $HTTP_BASE.($U_CGI =~ m#(^/~[^/]+)# ? $1:"")."/$doc_root";
}

################################################################################
# Config
process_cfg();
if($TIME_ZONE ne ""){
	if($TIME_ZONE =~ m/^gmt([+-])([0-9]+)$/i){
		$TIME_ZONE = "GMT".($1 eq "+" ? "-" : "+").$2;
	}

	$ENV{TIME_ZONE} = $TIME_ZONE;
	eval "use POSIX; POSIX::tzset();";
}
$CSS = -f "$TPL/uniqki.css" ? "$TPL/uniqki.css" : "$U_CGI?css";
my ($page_name_case, $page_name_spaces) = config_page_name_style();
my ($nonwiki_read_access, $wiki_read_access, $wiki_write_access) =
	config_read_write_access();

################################################################################
# Messages
process_msg();

################################################################################
# Initialization
$USER = "";
$ADMIN = 0;
my $header_printed = 0;
my $footer_printed = 0;
my $rebuild = 0;
my $insecure_pw = 1;
my $sessions_file = ".sessions";
my $debug_started = 0;
my $html_started = 0;

################################################################################
# Non-user-replaceable subroutines
#-------------------------------------------------------------------------------
# sha1_hex routine for password hashing
eval "use Digest::SHA qw(sha1_hex);";
if($@){
	sub sha1_hex{
		my $str = shift;
		$str =~ s/'/'"'"'/g;
		return substr `printf '%s' '$str' | sha1sum`, 0, 40;
	}
}

sub debug{
	my $msg = shift;
	unless($debug_started){
		$debug_started = 1;
		print "Content-Type: text/plain\n\n";
	}
	printf "%s\n", $msg;
}

sub config_page_name_style{
	my ($case, $spaces);

	foreach my $item (split /:/, $PAGE_NAME_STYLE){
		if("_case" eq substr $item, -5){
			$case = $item;
		}else{
			$spaces = $item;
		}
	}

	if($case eq "lower_camel_case"){
		$spaces = "no_spaces";
	}elsif($case eq "upper_camel_case"){
		$case = "start_case";
		$spaces = "no_spaces";
	}elsif($case ne "mixed_case" &&
		$case ne "upper_case" &&
		$case ne "start_case"){
		# default lower_case
		$case = "lower_case";
	}

	if($spaces ne "no_spaces" && $spaces ne "underscores"){
		# default hyphens
		$spaces = "hyphens";
	}
	return ($case, $spaces);
}

sub config_read_write_access{
	my @items = split /:/, $READ_ACCESS;
	my $nonwiki_read_access = $items[0] ne "open" && $items[0] ne "closed" ?
		"admin" : $items[0];
	my $wiki_read_access = $items[1] ne "open" && $items[1] ne "closed" ?
		"admin" : $items[1];
	my $wiki_write_access = $WRITE_ACCESS ne "open" &&
		$WRITE_ACCESS ne "closed" ? "admin" : $WRITE_ACCESS;
	return ($nonwiki_read_access, $wiki_read_access, $wiki_write_access);
}

sub exit_redirect{
	printf "Location: %s\n\n", shift;
	exit;
}

sub exit_message{
	local $MESSAGE = shift;
	(local $TITLE = $MESSAGE) =~ s/<[^>]*>//g;
	print_message();
	exit;
}

sub start_html{
	return if($html_started);
	$html_started = 1;
	print "Content-Type: text/html\n\n";
}

sub convert_page_name{
	my $page_name = shift;
	my $forbidden_chars = q(`~!@#\$%^&*=+\\|;:'",.\/?()\[\]{}<>);

	# from parse_line
	$page_name =~ y/\x01/&/;
	$page_name =~ y/\x02/</;
	$page_name =~ y/\x03/>/;

	$page_name =~ s/[$forbidden_chars]//g;
	$page_name =~ s/([ \t_-])+/ /g;
	$page_name =~ s/^ | $//g;
	return "" if($page_name eq "");

	if($page_name_case eq "mixed_case"){
		# case as is
	}elsif($page_name_case eq "upper_case"){
		$page_name = uc $page_name;
	}elsif($page_name_case eq "start_case"){
		$page_name =~ s/(?:^|(?<= ))([^ ])([^ ]*)/@{[(uc $1).(lc $2)]}/g;
	}elsif($page_name_case eq "lower_camel_case"){
		$page_name =~ s/^([^ ]*)/@{[lc $1]}/;
		$page_name =~ s/(?<= )([^ ])([^ ]*)/@{[(uc $1).(lc $2)]}/g;
	}else{
		# default: lower_case
		$page_name = lc $page_name;
	}

	if($page_name_spaces eq "no_spaces"){
		$page_name =~ y/ //d;
	}elsif($page_name_spaces eq "underscores"){
		$page_name =~ y/ /_/;
	}else{
		# default: hyphens
		$page_name =~ y/ /-/;
	}

	return $page_name;
}

sub escape_inline_syntax{
	my $code = shift;
	$code =~ s#([{"/*'-_|\[])\1#$1\x00$1#g;
	$code =~ s/\x00([&<>])/$1/g;
	$code =~ s/($protocol)/\x00$1/ogi;
	return $code;
}

sub link_path{
	my ($path, $title) = @_;

	$path =~ s/^[ \t]+|[ \t]+$//g;
	$title =~ s/^[ \t]+|[ \t]+$//g;

	my ($page, $file);

	my $i = rindex($path, "/");
	if($i >= 0){
		$page = substr $path, 0, $i;
		$file = substr $path, $i + 1;
	}else{
		$page = $path;
		$file = "";
	}

	my $enc_page = convert_page_name($page);
	return "" if($enc_page eq "");

	if($file eq ""){
		return qq(<a href="$enc_page/">$page</a>) if($title eq "");
		return qq(<a href="$enc_page/">$title</a>);
	}

	return qq(<a href="$enc_page/$file">$page/$file</a>) if($title eq "");
	return qq(<a href="$enc_page/$file">$title</a>);
}

sub link_page{
	my ($page, $section, $title) = @_;

	$page =~ s/^[ \t]+|[ \t]+$//g;
	$section =~ s/^[ \t]+|[ \t]+$//g;
	$title =~ s/^[ \t]+|[ \t]+$//g;

	my $enc_page = convert_page_name($page);
	my $enc_section = convert_page_name($section);

	if($enc_page eq ""){
		return "" if($enc_section eq "");
		return qq(<a href="#$enc_section">#$section</a>) if($title eq "");
		return qq(<a href="#$enc_section">$title</a>);
	}
	if($enc_section eq ""){
		return qq(<a href="$enc_page.html">$page</a>) if($title eq "");
		return qq(<a href="$enc_page.html">$title</a>);
	}
	return qq(<a href="$enc_page.html#$enc_section">$page#$section</a>) if($title eq "");
	return qq(<a href="$enc_page.html#$enc_section">$title</a>);
}

sub link_url{
	my ($url, $title) = @_;

	$url =~ s/^[ \t]+|[ \t]+$//g;
	$title =~ s/^[ \t]+|[ \t]+$//g;

	return qq(<a href="$url">$url</a>) if($title eq "");
	return qq(<a href="$url">$title</a>);
}

sub is_url{
	my $url = shift;

	# from parse_line
	$url =~ y/\x01/&/;

	# https://en.wikipedia.org/wiki/Percent-encoding
	return $url =~ m/^(?:$protocol)[%!*'();:@&=+\$,\/?#\[\]a-zA-Z0-9_.~-]+$/o;
}

sub encode_url{
	my $url = shift;

	# from parse_line
	$url =~ y/\x01/&/;

	# https://en.wikipedia.org/wiki/Percent-encoding
	$url =~ s/([^!*'();:@&=+\$,\/?#\[\]a-zA-Z0-9_.~-])/@{[sprintf "%%%x", ord($1)]}/g;
	return $url;
}

sub create_table_cell{
	my ($colspan, $rowspan, $left, $content, $right) = @_;

	$colspan = length($colspan);
	$rowspan = length($rowspan) + 1;
	$left = length($left);
	$right = length($right);

	$rowspan = $rowspan == 1 ? "" : qq( rowspan="$rowspan");
	$colspan = $colspan == 1 ? "" : qq( colspan="$colspan");
	my $align = $left == 0 ? "left" : ($right == 0 ? "right" : "center");
	return qq(<td$rowspan$colspan class="table_$align">$content</td>);
}

sub is_logged_in{
	return $USER ne "";
}

sub has_read_access{
	return 1 if($ADMIN);
	if($wiki){
		return 1 if($wiki_read_access eq "open");
		return 1 if($wiki_read_access eq "closed" && is_logged_in());
		return 0;
	}
	return 1 if($nonwiki_read_access eq "open");
	return 1 if($nonwiki_read_access eq "closed" && is_logged_in());
	return 0;
}

sub has_write_access{
	return 1 if($ADMIN);
	return 0 unless($wiki);
	return 1 if($wiki_write_access eq "open");
	return 1 if($wiki_write_access eq "closed" && is_logged_in());
	return 0;
}

sub page_exists{
	my $page = shift;
	$page = $PAGE unless(defined $page);
	return -f "$page.txt";
}

#-------------------------------------------------------------------------------
# Password file
sub write_pw{
	my $file;
	if($PW eq ""){
		$file = "u.pw";
	}else{
		$file = $PW;
	}
	unless(-f $file){
		open FH, ">$file";
		print FH "$adminpw\n";
		close FH;
	}
}

#-------------------------------------------------------------------------------
# Default config
sub process_cfg{
	# $mode=undef: eval
	# $mode=1: write
	my $mode = shift;
	my $cfg = <<'EOT_UNIQKI';
# RSS information
$RSS_TITLE = "Uniqki: A Personal Wiki Builder! http://uniqki.isnew.info";
$RSS_DESCRIPTION = "This site is powered by Uniqki! http://uniqki.isnew.info";

# Set time zone if different from the system time
$TIME_ZONE = "";

# Password file: The admin password can be embedded in the script as $adminpw.
$PW = "u.pw";

# Template files: The system default ones will be served by u.cgi if missing.
$TPL = "u.tpl";

# Message file: The system default messages will be printed if missing.
$MSG = "u.msg";

# Character set
$CHARSET = "utf-8";

# Login session will be extended by this number of minutes whenever any action
# is taken by the user.
$INACTIVE_TIMEOUT = 24*60;

# Change password timeout in minutes
$SET_PASSWORD_TIMEOUT = 60;

# Reset password timeout in minutes
$RESET_PASSWORD_TIMEOUT = 1;

# Email address for user management
$EMAIL_ADDRESS = "";

# Page name style: case[:underscores|:hyphens|:no_spaces]
# lower_case (default): All lower case (e.g., page in a uniqki site)
# upper_case: All upper case (e.g., PAGE IN A UNIQKI SITE)
# mixed_case: No special handling of letter case (e.g., Page in a Uniqki site)
# start_case: Start case (e.g., Page In A Uniqki Site)
# lower_camel_case: Lower camel case (e.g., pageInAUniqkiSite)
# upper_camel_case: Upper camel case (e.g., PageInAUniqkiSite)
#
# Optionally
# hyphens (default): Replace a series of whitespaces with a hyphen
# underscores: Replace a series of whitespaces with an underscore
#	       no_spaces: Remove whitespaces.  The lower_camel_case and
#	       upper_camel_case styles imply this option.  For example,
#	       upper_camel_case is the same as start_case:no_spaces.
#
# The following special characters will be removed before a case conversion.
# Forbidden characters in file names: `~!@#$%^&*+=\|;:'",/?()[]{}<>
#
# Hyphens (-) and underscores (_) will be converted to spaces and may be
# converted back to hyphens or underscores depending on the page name style.
#
# For example, "'page' in a uniqki site!!!" excluding double quotes in the
# start_case style will create and link to Page_In_A_Uniqki_Site.html.  The
# same page name in the upper_camel_case style will use PageInAUniqkiSite.html.
$PAGE_NAME_STYLE = "lower_case:hyphens";

# Read access control
# open: Opens both non-wiki and wiki pages to the public and anyone will be
# 	able to read those pages with or without a login.
# closed: Requires a login to perform any read actions including search, diff,
# 	  etc.  In addition, the following directives in .htaccess will prevent
# 	  direct access to *.html files, effectively making the entire site
# 	  read-secured.
# admin: Allows only admin users access to non-wiki and wiki pages.  The
# 	 .htaccess directives are required.
#
# Non-wiki and wiki pages can have different settings separated by a colon.
# For example, closed:open means closed non-wiki and open wiki pages.  One
# setting applies to both non-wiki and wiki pages.  That is, open is the same
# as open:open (open non-wiki and open wiki).
#
# Unless this variable is open:open, the following .htaccess directives are
# required to secure *.html files:
# RewriteEngine On
# RewriteBase /
# RewriteRule ^$ u.cgi [R,L]
# RewriteRule ^([^/]*)\.html$ u.cgi/$1 [R,L]
# RewriteRule ^(u\.cgi/.*)\.html$ $1 [R,L]
$READ_ACCESS = "open";

# Write access control
# open: Allows anyone to edit or create wiki pages with or without a login.
# closed: Requires a login to edit or create wiki pages.
# admin: Requires admin rights to edit or create wiki pages.
#
# Creating new wiki pages also depends on $WIKI_NEW_PAGE.  For security
# reasons, non-wiki pages are writable only by admin users and this variable
# cannot affect that behavior.
$WRITE_ACCESS = "open";

# Header and footer files for the parser
$HEADER = "";
$FOOTER = "";

# Header and footer files for the wiki parser (#!wiki as the first line)
$WIKI_HEADER = "";
$WIKI_FOOTER = "";

# Regular expression for wiki page names that are allowed to be created by
# non-admin users
$WIKI_NEW_PAGE = q();

# Regular expression for file names that are allowed to be uploaded by
# non-admin users to a wiki page
$WIKI_UPLOAD = q(\.(png|gif|jpg|jpeg|txt|zip)$);
EOT_UNIQKI
	if($mode == 1){
		unless(-f "u.cfg"){
			open FH, ">u.cfg";
			print FH $cfg;
			close FH;
		}
	}else{
		eval $cfg;
		do "u.cfg" if(-f "u.cfg");
	}
}

#-------------------------------------------------------------------------------
# Default messages
sub process_msg{
	# $mode=undef: eval if file does not exist, do file otherwise
	# $mode=1: write
	my $mode = shift;
	my $msg = <<'EOT_UNIQKI';
%MESSAGES = (
	perl_module_not_installed => q(%s: Perl module not installed.),
	read_secured => q(This Uniqki site is read-secured until you <a href="?login">login</a>.),
	write_secured => q(This Uniqki site is write-secured until you <a href="?login">login</a>.),
	login_not_allowed => q(Login is not allowed!),
	login_failed => q(Login failed!),
	no_admin_actions_allowed => q(No admin actions allowed! Please <a href="?login">login</a> first.),
	page_not_found => q(%s: Page not found!),
	create_page => q(%s: Page not found! <a href="?edit">Create this page</a>),
	specify_comment_page => q(Please specify a comment page!),
	comment_tag_not_found => q(%s: Comment tag not found!),
	invalid_user_management_mode => q(%s: Invalid user management mode! <a href="?admin">Go back to the admin page</a>),
	enter_user_id => q(Please enter a user ID to manage. <a href="?admin">Go back to the admin page</a>),
	check_user_id => q(Please enter a user ID that meets character requirements. <a href="?admin">Go back to the admin page</a>),
	user_already_blocked => q(%s: User already blocked. <a href="?admin">Go back to the admin page</a>),
	user_already_unblocked => q(%s: User already unblocked. <a href="?admin">Go back to the admin page</a>),
	only_user_cannot_be_deleted => q(%s: The only user cannot be deleted. <a href="?admin">Go back to the admin page</a>),
	only_user_cannot_be_blocked => q(%s: The only user cannot be blocked. <a href="?admin">Go back to the admin page</a>),
	only_user_cannot_be_unblocked => q(%s: The only user cannot be unblocked. <a href="?admin">Go back to the admin page</a>),
	enter_email_address => q(Please enter an email address. <a href="?admin">Go back to the admin page</a>),
	invalid_email_address => q(%s: Invalid email address! <a href="?admin">Go back to the admin page</a>),
	confirm_password => q(Please confirm the password. <a href="?admin">Go back to the admin page</a>),
	leave_email_address_blank => q(Please leave the email address blank. <a href="?admin">Go back to the admin page</a>),
	leave_password_blank => q(Please leave the password blank. <a href="?admin">Go back to the admin page</a>),
	check_password_requirements => q(Please enter a password that meets the length and character requirements. <a href="?admin">Go back to the admin page</a>),
	user_already_exists => q(%s: User already exists! <a href="?admin">Go back to the admin page</a>),
	email_address_already_registered => q(%s: Email address already registered! <a href="?admin">Go back to the admin page</a>),
	enter_user_info_to_update => q(%s: Please enter user information to update! <a href="?admin">Go back to the admin page</a>),
	user_not_found => q(%s: User not found! <a href="?admin">Go back to the admin page</a>),
	new_user_email_subject => q(%s: Registered),
	new_user_email_text => q(Your user ID %s is registered at %s. Please set your password by visiting %s within %d seconds.),
	unblocked_user_email_subject => q(%s: Unblocked),
	unblocked_user_email_text => q(Your user ID %s is unblocked at %s. Please set your password by visiting %s within %d seconds.),
	reset_password_email_subject => q(%s: Reset password),
	reset_password_email_text => q(Please reset your password for user ID %s at %s by visiting %s within %d seconds.),
	email_notification_failed => q(Email notification failed for user %s <%s>! <a href="?admin">Go back to the admin page</a>),
	change_admin_password => q(The admin password cannot be the same as the temporary password. Please use a different password. <a href="?admin">Go to the admin page</a>),
	session_errors => q(Session errors!),
	internal_errors => q(Internal errors!),

	current_version => q(The current version of page %s is %d.),

	file_uploaded => q(%s: File uploaded. Copy and paste the link below.),
	file_link_example => q(%s),

	not_wiki_page => q(%s: This page is not a wiki page.),
	not_allowed_to_create_nonwiki_page => q(%s: You are not allowed to create this non-wiki page.),
	not_allowed_to_edit_wiki_page => q(%s: You are not allowed to edit this wiki page.),
	not_allowed_to_edit_wiki_page => q(%s: You are not allowed to edit this wiki page.),
	goto_form_title => q(Goto form),
	search_form_title => q(Search form),
	comment_form_title => q(Comment form),
	recent_changes_title => q(Recent changes),
	recent_changes_matching_title => q(Recent changes matching %s pattern),
	old_changes_title => q(Old changes),
	old_changes_matching_title => q(Old changes matching %s pattern),
	all_pages_title => q(All pages),
	all_pages_matching_title => q(All pages matching %s pattern),
	all_pages_reversed_title => q(All pages in reversed order),
	all_pages_reversed_matching_title => q(All pages matching %s pattern in reverse order),
	refresh_title => q(Refresh pages),
	refresh_matching_title => q(Refresh pages matching %s pattern),
	search_title => q(Search for %s),
	search_matching_title => q(Search %s for %s),
	diff_title => q(Differences of page %s between versions %d and %d),

	goto_form_goto => q(Go to),
	search_form_search => q(Search),
	search_form_simple => q(Simple),
	search_form_link => q(Link),
	search_form_ignore_case => q(Ignore case),
	search_form_print_title => q(Print title),
	search_form_no_match => q(No match),
	comment_form_write => q(Write),

	table_of_contents => q(Table of contents),
);
EOT_UNIQKI
	my $file = "";
	if($MSG eq ""){
		$file = "u.msg";
	}else{
		$file = $MSG;
	}
	if($mode == 1){
		unless(-f $file){
			open FH, ">$file";
			print FH $msg;
			close FH;
		}
	}else{
		eval $msg;
		do $file if(-f $file);
	}
}

sub get_msg{
	my $msg_id = shift;
	return sprintf $MESSAGES{$msg_id}, @_;
}

sub is_user_id{
	my $id = shift;
	my $len = length($id);
	return $len >= 4 && $len <= 64 && $id =~ m/^[a-zA-Z0-9]+$/;
}

sub is_password{
	my $pw = shift;
	my $len = length($pw);
	return $len >= 8 && $len <= 128 &&
		$pw =~ m/[a-zA-Z]/ && $pw =~ m/[0-9]/ &&
		$pw =~ m/[`~!@#\$%^&*_+=\\|;:'",.\/?()\[\]{}<>]/;
}

sub is_email_address{
	# Regex: http://www.regular-expressions.info/email.html
	my $email_address = shift;
	my $len = length($email_address);
	return $len >= 6 && $len <= 254 &&
		$email_address =~ m/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
}

sub is_session_id{
	my $session_id = shift;
	my $len = length($session_id);
	return $len == 64 && $session_id =~ m/^[A-Za-z0-9]+$/;
}

#-------------------------------------------------------------------------------
# Default template
sub process_tpl{
	# $mode=undef: eval if file does not exist, do file otherwise
	# $mode=1: write
	# $mode=2: print for CSS only
	my ($file, $mode, $tpl) = @_;
	my $path = "$TPL/$file";

	start_html() unless(defined $mode);
	print "Content-Type: text/css\n\n" if($mode == 2);

	if($mode == 1){
		if(-d $TPL && !-f $path){
			open FH, ">$path";
			print FH $tpl;
			close FH;
		}
	}elsif(-f $path){
		if($mode == 2){
			open FH, $path;
			print <FH>;
			close FH;
		}else{
			do $path;
		}
	}elsif($mode == 2){
		print $tpl;
	}else{
		eval $tpl;
	}
}

sub print_header{
	my $mode = shift;
	return if(!defined $mode && $header_printed);

	$header_printed = 1;
	process_tpl("header.tpl", shift, <<'EOT_UNIQKI'
print <<EOT;
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>$TITLE</title>
<meta charset="$CHARSET" />
<meta name="viewport" content="width=device-width;" />
<link rel="stylesheet" type="text/css" href="$CSS" />
</head>
<body>
<div id="uniqki">
EOT
EOT_UNIQKI
	)
}

sub print_footer{
	my $mode = shift;
	return if(!defined $mode && $footer_printed);

	$footer_printed = 1;
	process_tpl("footer.tpl", $mode, <<'EOT_UNIQKI'
print <<EOT;
</div>
</body>
</html>
EOT
EOT_UNIQKI
	)
}

sub print_login{
	process_tpl("login.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="login">
<h1>$PAGE Login</h1>
<form action="$PAGE?login" method="post">
<div>
<input accesskey="i" type="text" id="id" name="id" placeholder="User ID" />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="Password" />
<input type="checkbox" id="logout_others" name="logout_others" value="1" /> Logout from other computers
<input accesskey="l" type="submit" value="Login" />
</div>
</form>
</div>
<div id="menu">
<hr />
<a accesskey="v" href="$DOC_BASE/$PAGE.html">View</a> .
<a accesskey="i" href="$DOC_BASE/index.html">Index</a>
</div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_admin{
	process_tpl("admin.tpl", shift, <<'EOT_UNIQKI'
print_header();
print qq(<div id="admin">
<h1>$PAGE Admin</h1>
<h2>Pages</h2>
<form action="?restore" method="post" enctype="multipart/form-data">
<div>
Backup: <a href="$SCRIPT_NAME?backup">All pages</a>).($PAGE eq "" ? "" : qq(
. <a href="?backup">$PAGE</a>)).qq(
<br />
Restore: <input accesskey="f" type="file" id="file" name="file" />
<input accesskey="r" type="submit" value="Restore" />
</div>
</form>

<h2>Users</h2>
<form action="?user" method="post">
<div>
<input type="radio" id="mode" name="mode" value="add">Add new user
<input type="radio" id="mode" name="mode" value="block">Block user
<input type="radio" id="mode" name="mode" value="unblock">Unblock user
<input type="radio" id="mode" name="mode" value="delete">Delete user
<input type="radio" id="mode" name="mode" value="update">Update user information
<br />
<input accesskey="i" type="text" id="id" name="id" placeholder="User ID" />
<input accesskey="e" type="text" id="email_address" name="email_address" placeholder="Email address" />
<input type="radio" id="admin" name="admin" value="no" /> Non-admin
<input type="radio" id="admin" name="admin" value="yes" /> Admin
<input type="radio" id="admin" name="admin" value="keep" /> Don't change
<br />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="Password" />
<input type="password" id="pw2" name="pw2" placeholder="Confirm password" />
<input accesskey="u" type="submit" value="Manage user" />
<br />
<ul>
<li>Add new user: Enter new user information and leave passwords blank for an email notification</li>
<li>Block/unblock/delete user: Enter an existing user ID</li>
<li>Change email address: Enter an existing user ID and type email address</li>
<li>Change password: Enter an existing user ID and type new password twice</li>
<li>User ID requirements: 4 or more letters (a-z, A-Z) and digits (0-9)</li>
<li>Password requirements: 8 or more characters with at least one letter (a-z, A-Z), one digit (0-9), and one special character excluding spaces and tabs</li>
</ul>
</div>
</form>
</div>
<div id="menu">
<hr />).($PAGE eq "" ? "" : qq(
<a accesskey="v" href="$DOC_BASE/$PAGE.html">view</a> .)).qq(
<a accesskey="i" href="$DOC_BASE/index.html">index</a>
<small><i>
Powered by <a href="http://uniqki.isnew.info">Uniqki</a>!
</i></small>
</div>
);
print_footer();
EOT_UNIQKI
	)
}

sub print_message{
	process_tpl("message.tpl", shift, <<'EOT_UNIQKI'
my $loginout = is_logged_in() ? "Logout" : "Login";
print_header();
print <<EOT;
<div id="message">
$MESSAGE
</div>
<div id="menu">
<hr />
EOT
if(has_read_access() && page_exists()){
	print qq(<a accesskey="v" href="$PAGE.html">View</a> .\n);
}
if(has_write_access()){
	my $edit = page_exists() ? "Edit" : "Create";
	print qq(<a accesskey="e" href="$PAGE?edit">$edit</a> .\n);
}
if(has_read_access() && $PAGE ne "index"){
	print qq(<a accesskey="i" href="index.html">Index</a> .\n);
}
print <<EOT;
<a accesskey="l" href="$PAGE?loginout">$loginout</a><br />
<small><i>
Powered by <a href="http://uniqki.isnew.info">Uniqki</a>!
</i></small>
</div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_view{
	# View templates are never served dynamically, so don't print a
	# content-type header
	$html_started = 1;
	process_tpl("view.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="view">
$TEXT
</div>
<!-- # --><div id="menu">
<!-- # --><hr />
<!-- # --><a accesskey="r" href="$U_CGI/$PAGE?refresh">Refresh</a> .
<!-- # --><a accesskey="e" href="$U_CGI/$PAGE?edit">Edit</a> .
<!-- # --><a accesskey="i" href="index.html">Index</a> .
<!-- # --><a accesskey="l" href="$U_CGI/$PAGE?loginout">Loginout</a><br />
<!-- # --><small><i>
<!-- # -->$TIME .
<!-- # --><a href="https://validator.w3.org/check?uri=referer">XHTML</a> .
<!-- # --><a href="https://jigsaw.w3.org/css-validator/check/referer">CSS</a> .
<!-- # -->Powered by <a href="http://uniqki.isnew.info">Uniqki</a>!
<!-- # --></i></small>
<!-- # --></div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_edit{
	process_tpl("edit.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="edit">
<h1>$PAGE Edit</h1>
<form action="$PAGE?edit" method="post" enctype="multipart/form-data">
<div>
<input type="hidden" id="version" name="version" value="$VERSION" />
<textarea accesskey="e" id="text" name="text" rows="24" cols="80">$TEXT</textarea>
<br />
<input accesskey="p" type="submit" id="preview" name="preview" value="Preview" />
<input accesskey="s" type="submit" id="save" name="save" value="Save" /> .
Upload <input accesskey="u" type="file" id="file" name="file" /> .
<a accesskey="c" href="$DOC_BASE/$PAGE.html">Cancel</a> .
<a accesskey="c" href="$DOC_BASE/index.html">Index</a>
</div>
</form>
</div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_preview{
	process_tpl("preview.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="preview">
$PREVIEW
</div>
EOT
print_edit();
print_footer();
EOT_UNIQKI
	)
}

sub print_updated{
	process_tpl("updated.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="updated">
<h1>$PAGE updated!</h1>
Please save your changes and read <a href="$DOC_BASE/$PAGE.html">the latest version</a>!
<br />
<textarea accesskey="e" id="text" name="text" rows="24" cols="80">$TEXT</textarea>
</div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_wikiview{
	# View templates are never served dynamically, so don't print a
	# content-type header
	$html_started = 1;
	process_tpl("wikiview.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="wikiview">
$TEXT
</div>
<!-- # --><div id="wikimenu">
<!-- # --><a accesskey="e" href="$U_CGI/$PAGE?wikiedit">EditPage</a> .
<!-- # --><a accesskey="d" href="$U_CGI/$PAGE?diff=-1">Diff</a> .
<!-- # --><a accesskey="l" href="$U_CGI?search=$PAGE%5C.html&amp;link=1">BackLink</a> .
<!-- # --><a accesskey="i" href="index.html">Index</a><br />
<!-- # --><small><i>
<!-- # -->$TIME .
<!-- # --><a href="https://validator.w3.org/check?uri=referer">XHTML</a> .
<!-- # --><a href="https://jigsaw.w3.org/css-validator/check/referer">CSS</a> .
<!-- # -->Powered by <a href="http://uniqki.isnew.info">Uniqki</a>!
<!-- # --></i></small>
<!-- # --></div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_wikiedit{
	process_tpl("wikiedit.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="wikiedit">
<h1>$PAGE?wikiedit</h1>
<form action="$PAGE?wikiedit" method="post" enctype="multipart/form-data">
<div>
<input type="hidden" id="version" name="version" value="$VERSION" />
<textarea accesskey="e" id="text" name="text" rows="24" cols="80">$TEXT</textarea><br />
<input accesskey="p" type="submit" id="preview" name="preview" value="Preview" />
<input accesskey="s" type="submit" id="save" name="save" value="Save" /> .
EOT
if($WIKI_UPLOAD ne ""){
	print <<EOT;
Upload <input accesskey="u" type="file" id="file" name="file" /> .
EOT
}
print <<EOT;
<a accesskey="c" href="$DOC_BASE/$PAGE.html">Cancel</a>
</div>
</form>
</div>
EOT
print_footer();
EOT_UNIQKI
	)
}

sub print_wikipreview{
	process_tpl("wikipreview.tpl", shift, <<'EOT_UNIQKI'
print_header();
print <<EOT;
<div id="wikipreview">
$PREVIEW
</div>
EOT
print_wikiedit();
print_footer();
EOT_UNIQKI
	)
}

sub print_css{
	process_tpl("uniqki.css", shift, <<'EOT_UNIQKI'
/******************************************************************************/
body {
	background-color:	#eeeeee;
}
h1 {
	margin-top:		0px;
}
form {
	margin:			0px;
}
pre {
	background-color:	#dddddd;
	overflow:		auto;
}
textarea {
	width:			100%;
}

/******************************************************************************/
#uniqki {
	background-color:	white;
	border:			1px solid #aaaaaa;
	max-width:		960px;
	margin:			auto;
	padding:		10px;
	box-shadow:		5px 5px 5px #aaaaaa;
}
#login {
}
#admin {
}
#message {
}
#menu {
}

/******************************************************************************/
#view {
}
#edit {
}
#preview {
}
#updated {
}
#file_uploaded {
}
#file_link_example {
	border-bottom:		1px dashed #999999;
	padding-bottom:		20px;
}

/******************************************************************************/
#wikiview {
	background-color:	#eeeeee;
	color:			#000000;
	border:			1px solid #999999;
	padding:		5px;
}
#wikiedit {
}
#wikipreview {
}
#wikimenu {
	padding:		5px;
}

/******************************************************************************/
#toc {
	padding-bottom:		1px;
}
.toc_heading {
	font-weight:		bold;
}
.toc_list {
}
.table {
	border-collapse:	collapse;
}
.table td {
	border:			1px solid #999999;
	padding:		3px;
}
.table_left {
	text-align:		left;
}
.table_center {
	text-align:		center;
}
.table_right {
	text-align:		right;
}

/******************************************************************************/
#diff {
}
.diff_unchanged {
	font-family:		monospace;
}
.diff_added {
	background-color:	#66cccc;
	color:			#000000;
	font-family:		monospace;
}
.diff_deleted {
	background-color:	#ff99cc;
	color:			#000000;
	font-family:		monospace;
	text-decoration:	line-through;
}
.diff_modified {
	background-color:	#cccccc;
	color:			#000000;
	font-family:		monospace;
}
.diff_modified_added {
	background-color:	#66cccc;
	color:			#000000;
	font-family:		monospace;
}
.diff_modified_deleted {
	background-color:	#ff99cc;
	color:			#000000;
	font-family:		monospace;
	text-decoration:	line-through;
}

/******************************************************************************/
#ls {
}
.ls_time {
	font-size:		70%;
	font-style:		italic;
}

/******************************************************************************/
.goto_input {
}

/******************************************************************************/
#search {
}
.search_highlight {
	font-weight:		bold;
}
.search_input {
}

/******************************************************************************/
.comment_input {
	border-top:		1px solid #aaaaaa;
	margin-top:		10px;
	padding-top:		10px;
}
EOT_UNIQKI
	)
}

#-------------------------------------------------------------------------------
# Text file subroutines
sub lcs{
	my ($c0, $c1) = @_;
	my @lcs;
	my $s;
	for($s=0; $s<=$#$c0&&$s<=$#$c1; $s++){
		last if($$c0[$s] ne $$c1[$s]);
	}
	my ($e0, $e1);
	for($e0=$#$c0,$e1=$#$c1; $e0>$s&&$e1>$s; $e0--,$e1--){
		last if($$c0[$e0] ne $$c1[$e1]);
	}
	my ($m, $n);
	for($m=$s; $m<=$e0; $m++){
		for($n=$s; $n<=$e1; $n++){
			if($$c0[$m] eq $$c1[$n]){
				if($m && $n){
					$lcs[$m][$n] = $lcs[$m-1][$n-1] + 1;
				}else{
					$lcs[$m][$n] = 1;
				}
			}elsif($m && $n && $lcs[$m][$n-1]+0 > $lcs[$m-1][$n]+0){
				$lcs[$m][$n] = $lcs[$m][$n-1] + 0;
			}else{
				if($m){
					$lcs[$m][$n] = $lcs[$m-1][$n] + 0;
				}else{
					$lcs[$m][$n] = 0;
				}
			}
		}
	}
	my $i = $lcs[$e0][$e1];
	my @delta;
	$delta[$i] = ($e0+1).",".($e1+1);
	for($m=$e0,$n=$e1; $i>0&&$m>=$s&&$n>=$s; $m--,$n--){
		if($$c0[$m] eq $$c1[$n]){
			$delta[--$i] = "$m,$n";
		}elsif($lcs[$m][$n-1] > $lcs[$m-1][$n]){
			$m++;
		}else{
			$n++;
		}
	}
	return ($s, @delta);
}

sub diff{
	my @line0 = split /\n/, $_[0], -1;
	my @line1 = split /\n/, $_[1], -1;
	my ($s, @delta) = lcs(\@line0, \@line1);
	my ($m, $n) = ($s, $s);
	my $diff = "";
	for(my $i=0; $i<=$#delta; $i++,$m++,$n++){
		my ($x, $y) = split /,/, $delta[$i];
		if($x > $m){
			for(; $m<$x; $m++){
				$diff .= "-$m\n";
			}
		}
		if($y > $n){
			for(; $n<$y; $n++){
				$diff .= "+$m $line1[$n]\n";
			}
		}
	}
	return $diff;
}

sub patch{
	my @line0 = split /\n/, $_[0], -1;
	my @lined = split /\n/, $_[1];
	my $line0p = "";
	for(my $i=0; $i<=$#lined; $i++){
		if($lined[$i] =~ m/^\+/){
			my $p = index $lined[$i], " ";
			my $j = substr $lined[$i], 1, $p-1;
			my $l = substr $lined[$i], $p+1;
			if($j){
				$line0[$j-1] .= "\n$l";
			}else{
				$line0p .= "$l\n";
			}
		}else{
			$line0[substr $lined[$i], 1] = "\x00";
		}
	}
	$line0[0] = "$line0p$line0[0]";
	my $str = join "\n", @line0;
	$str .= "\n";
	$str =~ s/\x00\n//g;
	return $str;
}

sub save{
	local *FH;
	my ($PAGE, $TEXT) = @_;
	if(-f "$PAGE.txt"){
		my $version = 0;
		my $txtv = "";
		if(open FH, "$PAGE.txt.v"){
			my $line = <FH>;
			{
				local $/ = undef;
				$txtv = $line.<FH>;
			}
			close FH;
			my @items = split /:/, $line;
			$version = $items[0];
		}
		local $/ = undef;
		open FH, "$PAGE.txt";
		my $text = <FH>;
		close FH;
		my $diff = diff($TEXT, $text);
		if($diff ne ""){
			$version++;
			my $time = time;
			$txtv = "$version:$USER:$time\n$diff\x00\n$txtv";
			open FH, ">$PAGE.txt.v";
			print FH $txtv;
			close FH;
		}
	}
	if(open FH, ">$PAGE.txt"){
		print FH $TEXT;
		close FH;
		$rebuild = 1;
	}
}

sub get_version{
	local *FH;
	my $PAGE = shift;
	my $version = 0;
	if(open FH, "$PAGE.txt.v"){
		my @items = split /:/, <FH>;
		close FH;
		$version = $items[0] + 1;
		exit_message(get_message("internal_errors")) unless(-f "$PAGE.txt");
	}elsif(-f "$PAGE.txt"){
		$version = 1;
	}
	return $version;
}

sub lock_file{
	local *FH;
	my $timeout = 60;
	my $i = 0;
	while(-f "$_[0].lock"){
		exit_message(get_message("internal_errors")) if(++$i > $timeout);
		sleep 1;
	}
	exit_message(get_message("internal_errors")) unless(open FH, ">$_[0].lock");
	close FH;
}

sub unlock_file{
	unlink "$_[0].lock";
}

sub preview{
	local $PAGE = shift;
	local $TEXT = shift;
	my $uploaded = shift;
	my $wikiedit = shift;

	local *FH;
	my $txt;

	local $TITLE = "";
	local $PREVIEW;
	local $wiki;

	open FH, ">", \$txt;
	print FH ($wikiedit ? "#!wiki\n" : "")."$TEXT\n";
	close FH;

	$PREVIEW = parse_file(\$txt);
	chomp $PREVIEW;

	$TITLE = $PAGE if($TITLE eq "");
	$PREVIEW = $uploaded.$PREVIEW;
	$TEXT =~ s/&/&amp;/g; $TEXT =~ s/</&lt;/g; $TEXT =~ s/>/&gt;/g;

	if($wikiedit){
		print_wikipreview();
	}else{
		print_preview();
	}
}

sub make_html{
	local $PAGE = shift;
	local *FH;
	my $txt;

	local $TITLE = "";
	local $TEXT;
	local $wiki;

	$txt = "$PAGE.txt";
	$TEXT = parse_file($txt);
	chomp $TEXT;

	$TITLE = $PAGE if($TITLE eq "");
	local $TIME = scalar localtime((stat "$PAGE.txt")[9]);

	my $html;
	open FH, ">", \$html; my $fh = select FH;
	if($wiki){
		print_wikiview();
	}else{
		print_view();
	}
	close FH; select $fh;
	$html =~ s/\r//g;

	lock_file("$PAGE.html");
	open FH, ">$PAGE.html";
	print FH $html;
	close FH;
	chmod 0755, "$PAGE.html" if($HOSTING eq "awardspace");
	unlock_file("$PAGE.html");
}

sub rmrf{
	local *DH;
	foreach(@_){
		if(-f $_){
			unlink $_;
		}elsif(-d $_){
			my $dir = $_;
			opendir DH, $dir;
			my @i = map {"$dir/$_"} grep !/^\.{1,2}$/, readdir DH;
			closedir DH;
			rmrf(@i);
			rmdir $dir;
		}
	}
}

sub rmdirp{
	foreach(@_){
		my $dir = $_;
		while(index($dir, "/") >= 0){
			rmdir $dir;
			$dir =~ s#/[^/]*$##;
		}
		rmdir $dir;
	}
}

sub find{
	my $file = shift;
	if(-d $file){
		local *DH;
		my @list;
		opendir DH, $file;
		foreach(sort readdir DH){
			next if($_ eq "." || $_ eq "..");
			push @list, find("$file/$_");
		}
		closedir DH;
		return @list;
	}elsif(-f $file){
		return $file;
	}
}

sub get_var{
	my (%var, $v);
	foreach(split /&/, $QUERY_STRING){
		m/^([^=]*)=(.*)$/;
		$v = $1; $var{$v} = $2;
		$var{$v} =~ y/+/ /; $var{$v} =~ s/%0D//g;
		$var{$v} =~ s/%(..)/pack "c", hex($1)/eg;
	}
	my $boundary = <STDIN>;
	if("-" eq substr $boundary, 0, 1){
		read STDIN, my $content, $CONTENT_LENGTH-length($boundary);
		$content = $boundary.$content;
		(my $b = $boundary) =~ s/\r\n$//;
		$content =~ s/^$boundary//;
		$content =~ s/\r\n$b--\r\n$//;
		foreach(split /\r\n$boundary/, $content){
			my ($header, $body) = m/(.*?)\r\n\r\n(.*)$/s;
			$header =~ m/ name="(.*?)"/;
			my $name = $1;
			if($header =~ m/ filename="(.*?)"/){
				($var{$name} = $1) =~ s#^.*[/\\]##;
				$var{"$name="} = $body;
			}else{
				$body =~ s/\r//g;
				$var{$name} = $body;
			}
		}
	}else{
		foreach(split /&/, $boundary){
			m/^([^=]*)=(.*)$/;
			$v = $1; $var{$v} = $2;
			$var{$v} =~ y/+/ /; $var{$v} =~ s/%0D//g;
			$var{$v} =~ s/%(..)/pack "c", hex($1)/eg;
		}
	}
	return %var;
}

sub backup{
	eval "use Archive::Zip;";
	exit_message(get_msd("perl_module_not_installed", "Archive::Zip")) if($@);

	my $page = shift;
	my $zip = Archive::Zip->new();
	my $file;
	if($page eq ""){
		$file = "uniqki.zip";
		$zip->addTree(".");
	}else{
		$file = "$page.zip";
		foreach("txt", "txt.v", "html"){
			$zip->addFile("$page.$_") if(-f "$page.$_");
		}
		$zip->addTree($page, $page) if(-d $page);
	}
	print <<EOT;
Content-Type: application/zip
Content-Disposition: attachment; filename="$file"

EOT
	$zip->writeToFileHandle(*STDOUT);
}

sub restore{
	eval "use Archive::Zip;";
	exit_message(get_msd("perl_module_not_installed", "Archive::Zip")) if($@);

	my $boundary = <STDIN>;
	my $file = <STDIN>; my $tmp = $file.<STDIN>.<STDIN>;
	$file =~ s#^.*?filename="(.*?)".*$#$1#s; $file =~ s#^.*[/\\]##;
	my $length = $CONTENT_LENGTH - length($tmp) - 2 *
		length($boundary) - 4;
	read STDIN, my $content, $length;
	my ($fh, $name) = Archive::Zip::tempFile(".");
	print $fh $content;
	my $zip = Archive::Zip->new();
	$zip->readFromFileHandle($fh);
	(my $u_cgi = $U_CGI) =~ s#^(?:/~[^/]+)?/##;
	$zip->removeMember($u_cgi);
	$zip->removeMember($PW);
	foreach($zip->memberNames()){
		$zip->removeMember($_) if(-f $_ && !-w $_);
		if($HOSTING eq "awardspace" &&
			(m#\.html$# || m#/#)){
			my $member = $zip->memberNamed($_);
			$member->unixFileAttributes(0755);
		}
	}
	$zip->extractTree();
	close $fh;
	unlink $name;

	if($HOSTING eq "awardspace"){
		foreach($zip->memberNames()){
			chmod 0755, $_ if(m#\.html$# || m#/#);
		}
	}
}

sub set_cookie{
	my ($session_id, $expires) = @_;

	my @t = gmtime $expires;
	my @m = qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec);
	my @w = qw(Sun Mon Tue Wed Thu Fri Sat);
	my $expires = sprintf "%s, %02d-%s-%d %02d:%02d:%02d GMT",
		$w[$t[6]], $t[3], $m[$t[4]], $t[5]+1900, $t[2], $t[1], $t[0];

	print "Set-Cookie: uniqki=$session_id; domain=$HTTP_HOST; ".
		"path=$SCRIPT_NAME; expires=$expires; secure; httponly\n";
}

sub clear_cookie{
	print "Set-Cookie: uniqki=; domain=$HTTP_HOST; path=$SCRIPT_NAME; ".
		"expires=Tue, 01-Jan-1980 00:00:00 GMT; secure; httponly\n";
}

sub find_user_info{
	my $id = shift;
	local *FH;

	my $method = 0;
	# $method=0: No user found
	# $method=1: Use $PW
	# $method=2: Use $adminpw

	if($PW eq ""){
		# No password file is specified in u.cfg.  Since the password
		# file in the default config is u.pw, an empty $PW was assigned
		# by the user.
		if($adminpw eq $tmp_adminpw){
			# If $adminpw is still temporary, this situation can be
			# very dangerous because anyone can login using the
			# public temporary password.  Do not allow any login in
			# this case.
		}else{
			# If $adminpw has been changed, use this password.
			$method = 2;
		}
	}elsif(-f $PW){
		# Use the password file
		$method = 1;
	}elsif($adminpw eq $tmp_adminpw){
		# Password file does not exist and $adminpw is temporary.  The
		# first run of u.cgi is this case.  Create the password file
		# only for the login action immediately before checking
		# credentials against the temporary password to avoid timing
		# attacks.
		$method = 2;
	}else{
		# Password file does not exist and $adminpw has been changed.
		# Assume that the user deleted the password file intentionally
		# for single file operations.
		$method = 2;
	}
	return if($method == 0);

	my $userline = "";
	if($method == 1){
		open FH, $PW;
		my @lines = grep /^$id:/, <FH>;
		close FH;

		if($#lines == 0){
			$userline = $lines[0];
			$userline =~ s/[\r\n]//;
		}
	}elsif($method == 2 && "$id:" eq substr $adminpw, 0, length("$id:")){
		$userline = $adminpw;
	}
	return if($userline eq "");

	my @items = split /:/, $userline;
	return @items[1..$#items];
}

sub authenticate_user{
	my ($id, $pw, $logout_others) = @_;
	local *FH;

	my $method = 0;
	# $method=0: Login not allowed
	# $method=1: Create $PW and force to change the password
	# $method=2: Use $PW
	# $method=3: Use $adminpw

	if($PW eq ""){
		# No password file is specified in u.cfg.  Since the password
		# file in the default config is u.pw, an empty $PW was assigned
		# by the user.
		if($adminpw eq $tmp_adminpw){
			# If $adminpw is still temporary, this situation can be
			# very dangerous because anyone can login using the
			# public temporary password.  Do not allow any login in
			# this case.
			exit_message(get_msg("login_not_allowed"));
		}else{
			# If $adminpw has been changed, use this password.
			$method = 3;
		}
	}elsif(-f $PW){
		# Use the password file
		$method = 2;
	}elsif($adminpw eq $tmp_adminpw){
		# Password file does not exist and $adminpw is temporary.  The
		# first run of u.cgi is this case.  Create the password file
		# only for the login action immediately before checking
		# credentials against the temporary password to avoid timing
		# attacks.
		if($QUERY_STRING eq "login"){
			open FH, ">$PW";
			print FH "$adminpw\n";
			close FH;
			$method = 1;
		}
	}else{
		# Password file does not exist and $adminpw has been changed.
		# Assume that the user deleted the password file intentionally
		# for single file operations.
		$method = 3;
	}

	my ($saved_pw, $group, $email_address, $reset_hash) = find_user_info($id);
	if(!defined $saved_pw || $saved_pw eq "blocked"){
		close_session();
		exit_message(get_msg("login_failed"));
	}

	my $salt = substr $saved_pw, 0, 8;
	if($saved_pw ne hash_password($id, $pw, $salt)){
		close_session();
		exit_message(get_msg("login_failed"));
	}

	# If admin password is not temporary, the password is secure.
	my $idpw = "$id:$saved_pw:";
	$insecure_pw = 0 if($idpw ne substr $tmp_adminpw, 0, length($idpw));

	clear_sessions($id) if($logout_others eq "1");
	start_session($id);

	if($method == 1){
		# Force to change the password
		exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?admin");
	}

	$USER = $id;
	$ADMIN = 1 if($group eq "admin");
}

sub find_session_info{
	my $session_id = shift;
	local *FH;

	return if(!-f $sessions_file || !is_session_id($session_id));

	open FH, $sessions_file;
	my @lines = grep /^$session_id:/, <FH>;
	close FH;
	return if($#lines == -1);

	my @items = split /:/, $lines[0];
	return @items[1..$#items];
}

sub start_session{
	my $id = shift;
	my ($session_id, $expires) = generate_session_id($id);
	set_cookie($session_id, $expires);
}

sub renew_session{
	my $session_id = shift;
	local *FH;

	my $expires = time + $INACTIVE_TIMEOUT * 60;
	my $new_sessions = "";
	my $renewed = 0;

	open FH, $sessions_file;
	while(<FH>){
		if(m/^$session_id:/){
			$renewed = 1;
			my @items = split /:/;
			$_ = "$session_id:$items[1]:$items[2]:$expires\n";
		}
		$new_sessions .= $_;
	}
	close FH;

	if($renewed){
		lock_file($sessions_file);
		open FH, ">$sessions_file";
		print FH $new_sessions;
		close FH;
		unlock_file($sessions_file);

		set_cookie($session_id, $expires);
	}
}

sub close_session{
	clear_cookie();

	my $cookie = $HTTP_COOKIE; $cookie =~ s/; /\n/g;
	return unless($cookie =~ m/^uniqki=(.+)$/m);

	my $session_id = $1;
	return if(!-f $sessions_file || !is_session_id($session_id));

	my $new_sessions = "";
	my $deleted = 0;

	open FH, $sessions_file;
	while(<FH>){
		if(m/^$session_id:/){
			$deleted = 1;
			next;
		}
		$new_sessions .= $_;
	}
	close FH;

	if($deleted){
		lock_file($sessions_file);
		open FH, ">$sessions_file";
		print FH $new_sessions;
		close FH;
		unlock_file($sessions_file);
	}
}

sub clear_sessions{
	my $id = shift;

	unless(defined $id){
		clear_cookie();
		my $cookie = $HTTP_COOKIE; $cookie =~ s/; /\n/g;
		$cookie =~ m/^uniqki=(.+)$/m;
		my $session_id = $1;
		($id) = find_session_info($session_id);
	}
	return if(!-f $sessions_file || !is_user_id($id));

	my $new_sessions = "";
	my $deleted = 0;

	open FH, $sessions_file;
	while(<FH>){
		if(m/^[^:]*:$id:/){
			$deleted = 1;
			next;
		}
		$new_sessions .= $_;
	}
	close FH;

	if($deleted){
		lock_file($sessions_file);
		open FH, ">$sessions_file";
		print FH $new_sessions;
		close FH;
		unlock_file($sessions_file);
	}
}

sub handle_session{
	my $cookie = $HTTP_COOKIE; $cookie =~ s/; /\n/g;
	unless($cookie =~ m/^uniqki=(.+)$/m){
		clear_cookie();
		return;
	}

	my $session_id = $1;
	my ($id, $status, $expires) = find_session_info($session_id);

	unless(defined $id){
		clear_cookie();
		return;
	}
	if($status ne "active" || time > $expires){
		close_session();
		return;
	}
	my ($pw, $group, $email_address, $reset_hash) = find_user_info($id);
	unless(defined $pw){
		close_session();
		return;
	}

	renew_session($session_id);

	# If admin password is not temporary, the password is secure.
	my $idpw = "$id:$pw:";
	$insecure_pw = 0 if($idpw ne substr $tmp_adminpw, 0, length($idpw));

	$USER = $id;
	$ADMIN = 1 if($group eq "admin");
}

sub generate_random_string{
	my $len = shift;
	# http://www.perlmonks.org/?node_id=233023
	my @chars = ("A".."Z", "a".."z", "0".."9");
	my $str;
	$str .= $chars[rand @chars] for 1..$len;
	return $str;
}

sub generate_salt{
	return generate_random_string(8);
}

sub generate_session_id{
	my $id = shift;
	local *FH;
	my $session_id;
	my $i = 0;
	my $found;
	do{
		$session_id = generate_random_string(64);
		my @session = find_session_info($session_id);
		$found = defined $session[0] ? 1 : 0;
		$i++;
	}while($found && $i<10);

	exit_message(get_msg("session_errors")) if($found);

	my $expires = time + $INACTIVE_TIMEOUT * 60;

	lock_file($sessions_file);
	unless(open FH, ">>$sessions_file"){
		unlock_file($sessions_file);
		exit_message(get_msg("session_errors"));
	}
	print FH "$session_id:$id:active:$expires\n";
	close FH;
	unlock_file($sessions_file);

	return ($session_id, $expires);
}

sub generate_tmp_password{
	# SHA1 + !.../
	return sha1_hex(generate_salt()).chr(33+int(rand(15)));
}

sub hash_password{
	my ($id, $pw, $salt) = @_;
	$salt = generate_salt() unless(defined $salt);
	return $salt.sha1_hex("$id:$salt:$pw");

}

sub generate_set_password_hash{
	my $id = shift;
	return hash_password($id, generate_tmp_password()).".".
		(time + $SET_PASSWORD_TIMEOUT * 60);
}

sub generate_reset_password_hash{
	my $id = shift;
	return hash_password($id, generate_tmp_password()).".".
		(time + $RESET_PASSWORD_TIMEOUT * 60);
}

sub send_email{
	my ($email_address, $subject, $text) = @_;
	eval "use MIME::Lite";
	exit_message(get_msd("perl_module_not_installed", "MIME::Lite")) if($@);

	MIME::Lite->quiet(1);
	my $msg = MIME::Lite->new(
		From	=> $EMAIL_ADDRESS,
		To	=> $email_address,
		Subject	=> $subject,
		Data	=> $text
	);
	$msg->send();
	return $msg->last_send_successful();
}

sub create_goto_form{
	# $mode=undef: return
	# $mode=1: print
	my $mode = shift;
	my $goto = get_msg("goto_form_goto");
	my $form = <<EOT;
<form class="goto_input" action="$SCRIPT_NAME" method="get">
<div>
<input accesskey="g" id="goto" name="goto" />
<input type="submit" value="$goto" />
</div>
</form>
EOT
	if($mode == 1){
		print $form;
	}elsif($text ne ""){
		# Forms are not allowed inside a <p> block
		return "</p>$form<p>";
	}else{
		return $form;
	}
}

sub create_search_form{
	# $mode=undef: return
	# $mode=1: print
	my $mode = shift;
	my $search = get_msg("search_form_search");
	my $simple = get_msg("search_form_simple");
	my $link = get_msg("search_form_link");
	my $ignore_case = get_msg("search_form_ignore_case");
	my $print_title = get_msg("search_form_print_title");
	my $no_match = get_msg("search_form_no_match");
	my $form = <<EOT;
<form class="search_input" action="$SCRIPT_NAME" method="get">
<div>
<input accesskey="s" id="search" name="search" />
<input type="submit" value="$search" />
<input type="checkbox" id="simple" name="simple" value="1" checked="checked" /> $simple
<input type="checkbox" id="link" name="link" value="1" /> $link
<input type="checkbox" id="icase" name="icase" value="1" checked="checked" /> $ignore_case
<input type="checkbox" id="title" name="title" value="1" /> $print_title
<input type="checkbox" id="nomatch" name="nomatch" value="1" /> $no_match
</div>
</form>
EOT
	if($mode == 1){
		print $form;
	}elsif($text ne ""){
		# Forms are not allowed inside a <p> block
		return "</p>$form<p>";
	}else{
		return $form;
	}
}

sub create_comment_form{
	# $mode=undef: return
	# $mode=1: print
	my ($mode, $page, $comment, $direction, $rows, $cols) = @_;
	$page = $PAGE if($page eq "");
	$comment = "comment" if($comment eq "");
	$direction = "down" if($direction eq "");
	$rows = "6" if($rows eq "");
	$cols = "80" if($cols eq "");
	my $write = get_msg("comment_form_write");
	my $form = <<EOT;
<form class="comment_input" action="$SCRIPT_NAME?comment=$comment" method="post">
<div>
<input type="hidden" id="page" name="page" value="$page" />
<input type="hidden" id="direction" name="direction" value="$direction" />
<textarea accesskey="c" id="text" name="text" rows="$rows" cols="$cols"></textarea>
<input type="submit" value="$write" />
</div>
</form>
EOT
	if($mode == 1){
		print $form;
	}elsif($text ne ""){
		# Forms are not allowed inside a <p> block
		return "</p>$form<p>";
	}else{
		return $form;
	}
}

#-------------------------------------------------------------------------------
# User-replaceable subroutines
sub verify_input{
	return 1;
}

# Parsing subroutines
sub parse_file{
	my $file = shift;

	local *UNIQKI_FH;
	return unless(open UNIQKI_FH, "<", $file);
	$wiki = <UNIQKI_FH> eq "#!wiki\n" ? 1 : 0;
	close UNIQKI_FH;

	local ($text, $protocol, $protocol_char, $protocol_punct, $image_ext,
		$block, $re_i_start, $re_i, @re, @re_sub, $toc, $notoc,
		%h_i, $h_top, $h_prev, $p, $li_i, @li, @li_attr, $pre, $table);
	my ($header, $footer);

	unless($wiki){
		($header, $footer) = ($HEADER, $FOOTER);
	}else{
		($header, $footer) = ($WIKI_HEADER, $WIKI_FOOTER);
	}

	$begin_parsing = \&begin_parsing unless(defined($begin_parsing));
	$parse_line = \&parse_line unless(defined($parse_line));
	$end_parsing = \&end_parsing unless(defined($end_parsing));

	$begin_parsing->();
	foreach my $f ($header, $file, $footer){
		# "<" is required for the in-memory file
		next if($f eq "" || !open UNIQKI_FH, "<", $f);
		$parse_line->($_) while(<UNIQKI_FH>);
		close UNIQKI_FH;
	}
	$end_parsing->();

	return $text;
}

sub parse_text{
	my $txt = shift;
	local *UNIQKI_FH;

	local ($text, $protocol, $protocol_char, $protocol_punct, $image_ext,
		$block, $re_i_start, $re_i, @re, @re_sub, $toc, $notoc,
		%h_i, $h_top, $h_prev, $p, $li_i, @li, @li_attr, $pre, $table);
	my ($header, $footer);

	unless($wiki){
		($header, $footer) = ($HEADER, $FOOTER);
	}else{
		($header, $footer) = ($WIKI_HEADER, $WIKI_FOOTER);
	}

	$begin_parsing = \&begin_parsing unless(defined($begin_parsing));
	$parse_line = \&parse_line unless(defined($parse_line));
	$end_parsing = \&end_parsing unless(defined($end_parsing));

	$begin_parsing->();
	if($header ne "" && open UNIQKI_FH, "<", $header){
		$parse_line->($_) while(<UNIQKI_FH>);
		close UNIQKI_FH;
	}
	foreach my $line (split /\n/, $txt){
		$parse_line->($line);
	}
	if($footer ne "" && open UNIQKI_FH, "<", $footer){
		$parse_line->($_) while(<UNIQKI_FH>);
		close UNIQKI_FH;
	}
	$end_parsing->();

	return $text;
}

sub parse_block{
	my $txt = shift;

	local ($text);

	$parse_line = \&parse_line unless(defined($parse_line));

	foreach my $line (split /\n/, $txt){
		$parse_line->($line);
	}

	return $text;
}


sub begin_parsing{
	$protocol = 'https?://|ftp://|news://|telnet://|gopher://|wais://|mailto:|file://';
	$protocol_char = 'a-zA-Z0-9:@/~%.,_$?=&;#+-';
	$protocol_punct = '.,;:!?';
	$image_ext = 'png|gif|jpg|jpeg';

	$text = "";
	$block = "";
	$re_i_start = 0;
	$re_i = 0;
	@re = ();
	@re_sub = ();
	$toc = "";
	$notoc = 0;
	%h_i = ();
	$h_top = 0;
	$h_prev = 0;
	$p = 0;
	$li_i = 0;
	@li = ();
	@li_attr = ();
	$pre = 0;
	$table = 0;
}

sub parse_line{
	# \x00: NONE
	# \x01: &
	# \x02: <
	# \x03: >
	# \x04: place holder for auto-generated TOC
	# \x1e: delimiter
	# ##admin code
	# #user code
	# {{inline perl code}}
	# %comment
	local $_ = shift;
	s/[\r\n]//g;

	# Apply regular expressions where needed
	if(!$pre && m/^(?:(?!#)|#html )(.*)$/){
		for(my $i=$re_i_start; $i<$re_i; $i++){
			eval "s\x1e$re[$i]\x1e$re_sub[$i]\x1eg;";
		}
		if(m/\n/){
			local $re_i_start = $re_i;
			my @i = split /\n/, $_, -1;
			$parse_line->($_) foreach(@i);
			return;
		}
	}
	# Wiki but not pre
	if($wiki && !$pre){
		# Skip admin code
		return if("##" eq substr $_, 0, 2);
		# Ignore inline perl code
		s/{{(.*?)}}(?!})/{\x00{$1}\x00}/g;
	}
	# Process block admin code
	if($block ne ""){
		if($_ eq "##}"){
			my $i = "$block}";
			undef $block;
			$i =~ s/^(##[{}]_*)_$/$1/mg;
			eval $i;
			return;
		}
		$block .= "$_\n";
		return;
	}
	if(m/^(?![|#%]|{{.*?}}(?!}))/){
		# Close all lists if line is not another list item
		if($li_i > 0 && !(m/^(?:( *)[*+-]|:.*?:) / && length($1)%2 == 0)){
			while(--$li_i>=0){
				if($li[$li_i] eq "dl"){
					$text .= "</dd>\n";
				}else{
					$text .= "</li>\n";
				}
				$text .= "</$li[$li_i]>\n";
			}
			$li_i = 0;
		}
		# Close table
		if($table){
			$text .= "</table>\n";
			$table = 0;
		}
	}
	# Start or close pre
	if(m/^---+$/ && (!$pre || $pre == length)){
		if($pre){
			$text .= "</pre>\n";
			$pre = 0;
		}else{
			if($p){
				$text .= "</p>\n";
				$p = 0;
			}
			$text .= "<pre>\n";
			$pre = length;
		}
		return;
	}
	# Inside pre
	if($pre){
		s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g; s/\x00//g;
		$text .= "$_\n";
		return;
	}
	# Skip comment
	if("%" eq substr $_, 0, 1){
		return;
	}
	# Register regular expressions
	if(m/^#regex (.)([^\1]+)(?<!\\)\1([^\1]*)(?<!\\)\1$/){
		# In regex, \x00 can be used as an escape character.
		# \x00& => &, \x00< => <, \x00> => >

		# Don't allow delimiters
		return if(index($2, "\x1e") != -1 || index($3, "\x1e") != -1);

		# Don't allow code embedding in a wiki page
		return if($wiki && (index($2, '(?{') != -1 ||
			  	    index($2, '(??{') != -1 ||
				    index($3, '@{[') != -1));

		my $i;
		for($i=0; $i<$re_i; $i++){
			last if($re[$i] eq $2);
		}
		$re[$re_i++] = $2 if($i == $re_i);
		$_ = $3;
		# Don't allow access to variables in a wiki page
		s/\$/\\\$/g if($wiki);
		$re_sub[$i] = $_;
		return;
	}
	# Clear regular expressions
	if(m/^#noregex(?:| (.+))$/){
		if($1 eq ""){
			$re_i = 0;
			$#re = $#re_sub = -1;
		}else{
			for(my $i=0; $i<$re_i; $i++){
				if($re[$i] eq $1){
					$re_i--;
					for(; $i<$re_i; $i++){
						$re[$i] = $re[$i+1];
						$re_sub[$i] = $re_sub[$i+1];
					}
					$#re = $#re_sub = $re_i-1;
					last;
				}
			}
		}
		return;
	}
	# Output verbose html code
	if(m/^#html (.+)$/){
		$_ = $1;
		$text .= "$_\n";
		return;
	}
	# Table of contents
	if("#notoc" eq $_){
		$notoc = 1;
		return;
	}
	# Admin code starts
	if(m/^##include (.+)$/){
		local *FH;
		if(open FH, $1){
			$parse_line->($_) while(<FH>);
			close FH;
		}
		return;
	}
	if(m/^##shell (.+)$/){
		$_ = $1;
		$text .= `$_`;
		return;
	}
	if(m/^##((?:sub |{).*)$/){
		if("}" eq substr $1, -1){
			eval $1;
			return;
		}
		$block = "$1\n";
		return;
	}
	if("#" eq substr $_, 0, 1){
		return;
	}
	if(m/^___+$/){
		if($p){
			$text .= "</p>\n";
			$p = 0;
		}
		$text .= "<hr />\n";
		return;
	}
	# Close paragraph
	if("" eq $_){
		if($p){
			$text .= "</p>\n";
			$p = 0;
		}
		return;
	}
	s/""(.)(.*?)\1""/@{[escape_inline_syntax($2)]}/g;
	# Regular [&<>] should not be translated to html codes at this point
	# because page names and links will be affected.  Instead, flag them so
	# that they can be converted to html later.  This flagging does not
	# apply to escaped characters (\x00[&<>]).  Escaped characters may come
	# from the #regex syntax to enter [&<>] as is without converting them
	# to &amp, &lt, and &gt.
	s/(?<!\x00)&/\x01/g; s/(?<!\x00)</\x02/g; s/(?<!\x00)>/\x03/g;
	# Path links
	s#\[\[\[(.*?)(?:\|(.*?))?\]\]\]#@{[link_path($1, $2)]}#g;
	# Page links
	s#\[\[(.*?)(?:\#(.*?))?(?:\|(.*?))?\]\]#@{[link_page($1, $2, $3)]}#g;
	s#\x02\x02(.*?)(?:\|(.*?))?\x03\x03#@{[link_url($1, $2)]}#g;
	# Text styles
	# Avoid conflicts with //italic//
	s#($protocol)#$1\x00#ogi;
	s#//(?!\x00)(.*?)//(?!\x00)#<i>$1</i>#g;
	s#($protocol)\x00#$1#ogi;
	s#\*\*(.*?)\*\*#<b>$1</b>#g;
	s#''(.*?)''#<code>$1</code>#g;
	s#--(.*?)--#<s>$1</s>#g;
	s#__(.*?)__#<u>$1</u>#g;
	s#\|\|(.*?)\|\|#<mark>$1</mark>#g;
	# Percent-encode links inside tags
	s#(<[^>]*)(.)((?:$protocol)[^\2]*?)(\2[^>]*>)#$1$2@{[encode_url($3)]}$4#ogi;
	# Protect protocols inside a tag
	s#(<[^>]*)((?:$protocol)[^>]*>)#$1\x00$2#ogi;
	# Protect protocols outside a tag
	s#(<a [^>]*>[^<]*)((?:$protocol)[^<]*</a>)#$1\x00$2#ogi;
	# Translate non-protected protocols to links
	s#(?<![a-zA-Z\x00])((?:$protocol)[\x01$protocol_char]+\x01[a-z]+;)(?=(?:[ \t]|$))#<a href="\x00@{[encode_url($1)]}">\x00$1</a>#ogi;
	s#(?<![a-zA-Z\x00])((?:$protocol)[\x01$protocol_char]+)(?=[$protocol_punct](?:[ \t]|$))#<a href="\x00@{[encode_url($1)]}">\x00$1</a>#ogi;
	s#(?<![a-zA-Z\x00])((?:$protocol)[\x01$protocol_char]+)#<a href="\x00@{[encode_url($1)]}">\x00$1</a>#ogi;
	# Convert protected image links to image tags
	s#<a href="\x00([^"]+\.(?:$image_ext))">([^<]+)</a>#<img src="$1" alt="$2" title="$2" />#ogi;
	s/\x01/&amp;/g; s/\x02/&lt;/g; s/\x03/&gt;/g;
	# Start list
	if(m/^( *)([*+-]|:(.*?):) (.*)$/ && length($1)%2 == 0){
		my $i = length($1)/2+1;
		my $tag = substr $2, 0, 1;
		my $term = $3;
		my $item = $4;
		my $attr = "";
		if($tag eq "*"){
			$tag = "ul";
		}elsif($tag eq "+"){
			$tag = "ol";
		}elsif($tag eq "-"){
			$tag = "ol";
			$attr = q( reversed="reversed");
		}else{
			$tag = "dl";
		}
		if($p){
			$text .= "</p>\n";
			$p = 0;
		}
		if($i > $li_i){
			for(; $li_i<$i-1; $li_i++){
				$text .= "<$tag>\n";
				if($tag eq "dl"){
					$text .= "<dd>";
				}else{
					$text .= "<li>";
				}
				$li[$li_i] = $tag;
				$li_attr[$li_i] = "";
			}
			$text .= "<$tag$attr>\n";
			$li[$li_i] = $tag;
			$li_attr[$li_i++] = $attr;
		}elsif($i < $li_i){
			while(--$li_i>=$i){
				if($li[$li_i] eq "dl"){
					$text .= "</dd>\n";
				}else{
					$text .= "</li>\n";
				}
				$text .= "</$li[$li_i]>\n";
			}
			if($li[$li_i] eq $tag && $li_attr[$li_i] eq $attr){
				if($li[$li_i] eq "dl"){
					$text .= "</dd>\n";
				}else{
					$text .= "</li>\n";
				}
				$li_i++;
			}else{
				for(; $li_i>=0 && ($li[$li_i] ne $tag || $li_attr[$li_i] ne $attr); $li_i--){
					if($li[$li_i] eq "dl"){
						$text .= "</dd>\n";
					}else{
						$text .= "</li>\n";
					}
					$text .= "</$li[$li_i]>\n";
				}
				while(++$li_i<$i-1){
					$text .= "<$tag>\n";
					$li[$li_i] = $tag;
					$li_attr[$li_i] = "";
				}
				$text .= "<$tag$attr>\n";
				$li[$li_i] = $tag;
				$li_attr[$li_i++] = $attr;
			}
		}elsif($li[$li_i-1] ne $tag || $li_attr[$li_i-1] ne $attr){
			if($li[$li_i-1] eq "dl"){
				$text .= "</dd>\n";
			}else{
				$text .= "</li>\n";
			}
			$text .= "</$li[$li_i-1]>\n<$tag$attr>\n";
			$li[$li_i-1] = $tag;
			$li_attr[$li_i-1] = $attr;
		}elsif($tag eq "dl"){
			$text .= "</dd>\n";
		}else{
			$text .= "</li>\n";
		}

		if($tag eq "dl"){
			$_ = "<dt>$term</dt>\n<dd>$item";
		}else{
			$_ = "<li>$item";
		}
	}
	# Start table
	if(m/^\|+[0-9]*[ \t].*[ \t]\|$/){
		unless($table){
			if($p){
				$text .= "</p>\n";
				$p = 0;
			}
			$text .= "<table class=\"table\">\n";
			$table = 1;
		}
		$text .= "<tr>";
		# Empty cells
		s#(\|+)(_*)[ \t][ \t]*[ \t](?=\|)#@{[create_table_cell($1, $2)]}#g;
		# Non-empty cells
		s#(\|+)(_*)[ \t]([ \t]*)([^ \t].*?)([ \t]*)[ \t](?=\||<td)#@{[create_table_cell($1, $2, $3, $4, $5)]}#g;
		s/\|$//;
		$_ .= "</tr>";
	}
	# Inline perl code
	s/{{(.*?)}}(?!})/$1/eeg;
	# Discard NONE characters
	y/\x00//d;
	# Heading
	if(m/^(=+)!? (.*)$/ && length($1) <= 6){
		my $i = length($1);
		my $inc_toc = "!" ne substr $_, $i, 1 ? 1 : 0;
		$_ = $2;
		(my $t = $_) =~ s/<[^>]*>//g;
		$t =~ s/^ *//; $t =~ s/ *$//;
		my $id = $t;
		$id =~ s/&amp;/&/g; $id =~ s/&lt;/</g; $id =~ s/&gt;/>/g;
		$id = convert_page_name($id);
		my $j = $h_i{$id}++;
		if($j > 0){
			$id .= ".".($j+1);
		}
		if($p){
			$text .= "</p>\n";
			$p = 0;
		}
		if($i == 1){
			if($TITLE eq ""){
				$TITLE = $_;
				$TITLE =~ s/<[^>]*>//g;
			}
			$text .= qq(<h$i>$_</h$i>\n);
			return;
		}else{
			$text .= "\x04" if($toc eq "" && $inc_toc);
			$text .= qq(<h$i id="$id">$_</h$i>\n);
		}
		return unless($inc_toc);

		if($i > $h_prev){
			if($h_prev){
				$toc .= "<li><ul>" while($h_prev++<$i);
				$h_prev--;
			}else{
				$toc .= "<ul class=\"toc_list\">";
				$toc .= "\n" if($i > 1);
				$toc .= "<li><ul>" while(++$h_prev<$i);
				$h_top = $i;
			}
			$toc .= "\n";
		}elsif($i < $h_prev){
			$toc .= "</ul></li>" while(--$h_prev>=$i);
			$toc .= "\n";
			$h_prev++;
			$h_top = $i if($i < $h_top);
		}
		$toc .= "<li><a href=\"#$id\">$t</a></li>\n";
		return;
	}
	# Start a new paragraph
	if(!$li_i && !$pre && !$table && !$p){
		$text .= "<p>\n";
		$p = 1;
	}
	$text .= "$_\n";
}

sub end_parsing{
	if($li_i){
		while(--$li_i>=0){
			my $i = $li_i + 1;
			if($li[$li_i] eq "dl"){
				$text .= "</dd>\n";
			}else{
				$text .= "</li>\n";
			}
			$text .= "</$li[$li_i]>\n";
		}
		$text .= "<p>";
		$li_i = 0;
	}
	if($table){
		$text .= "</table>\n";
		$table = 0;
	}
	if($pre){
		$text .= "</pre>\n";
		$pre = 0;
	}
	if($p){
		$text .= "</p>\n";
		$p = 0;
	}
	if($notoc){
		$text =~ s/\x04//g;
	}elsif($h_prev){
		my $i = $h_prev;
		$toc .= "</ul></li>" while(--$h_prev>0);
		$toc .= ($i > 1 ? "\n" : "")."</ul>\n";
		for(my $i=0; $i<$h_top-1; $i++){
			$toc =~ s#^(.*\n)<li><ul>#\1#;
			$toc =~ s#</ul></li>(\n.*)$#\1#;
		}
		$toc =~ s#</li>\n<li>(<ul>)#\n\1#g;
		$toc =~ s#\n+#\n#g;
		my $heading = get_msg("table_of_contents");
		$toc = "<div id=\"toc\">\n".
			"<div class=\"toc_heading\">$heading</div>\n".
			"$toc</div>\n";
		$h_prev = 0;
		$text =~ s/\x04/$toc/g;
	}
	$text =~ s#<(p|i|b|code|su|mark)>([ \t\n]*)</\1>#$2#g;
	$text =~ s#(<(?:p|li|dd)>)\n+#$1#g; $text =~ s#\n+(</(?:p|li|dd)>)#$1#g;
}

if($PAGE eq $U_CGI && $FILE ne ""){
################################################################################
# u.cgi/u.cgi/.../PAGE?ACTION	Called from a secured site
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$FILE?$QUERY_STRING");
}

$PAGE = convert_page_name($PAGE);

################################################################################
# Login, logout
if($QUERY_STRING eq "logout"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?logout		Logout
	close_session();
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "logout_all"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?logout_all		Logout from all computers
	clear_sessions();
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "login" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?login		POST login request: Check credentials
	my %var = get_var();
	authenticate_user($var{id}, $var{pw}, $var{logout_others});
}else{
	handle_session();
	if($QUERY_STRING eq "login" && !is_logged_in()){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?login		GET login request: Login form
		print_login();
		exit;
	}
}

if($QUERY_STRING eq "loginout"){
#-------------------------------------------------------------------------------
# u.cgi?loginout		Loginout
# u.cgi/PAGE?loginout		Loginout
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?".
		(is_logged_in() ? "logout" : "login"));
}else{
#-------------------------------------------------------------------------------
# Is this page wiki?
	my $page;
	local *FH;
	if($PAGE eq "" && ($QUERY_STRING eq "login" || $QUERY_STRING eq "")){
		$page = "index";
	}else{
		$page = $PAGE;
	}
	$wiki = 0;
	if($page ne ""){
		if(-f "$page.txt"){
			open FH, "$page.txt";
			$wiki = 1 if(<FH> eq "#!wiki\n");
			close FH;
		}elsif($WIKI_NEW_PAGE ne "" && $page =~ m/$WIKI_NEW_PAGE/o){
			$wiki = 1;
		}
	}
}

if(!has_read_access()){
#-------------------------------------------------------------------------------
# Read-secured
	exit_message(get_msg("read_secured"));
}elsif($QUERY_STRING eq "login" || $QUERY_STRING eq ""){
#-------------------------------------------------------------------------------
# u.cgi?ACTION			User has to login to perform ACTION
# u.cgi/PAGE?ACTION		User has to login to perform ACTION
# u.cgi?login			After a successful login
# u.cgi/PAGE?login		After a successful login
# u.cgi				No action specified
# u.cgi/PAGE			No action specified
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/index") if($PAGE eq "");
	unless(-f "$PAGE.txt"){
		my $path = substr $PATH_INFO, 1;
		exit_redirect("$HTTP_BASE$PATH_INFO") if(-d $path || -f $path);

		my $msg_id = has_write_access() ?
			"create_page" : "page_not_found";
		exit_message(get_msg($msg_id, $PAGE));
	}
################################################################################
# User actions
}elsif($QUERY_STRING =~ m/^goto(?:[&=].+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?goto			Create the goto form
# u.cgi?goto=PAGE		Go to or create PAGE using a form (admin only)
	my %var = get_var();
	if($var{goto} eq ""){
		local $TITLE = get_msg("goto_form_title");
		print_header();
		create_goto_form(1);
		print_footer();
		exit;
	}

	$_ = $var{goto};
	s#/.*$##; s#\.html$##;
	y/+/ /;

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$_");
}elsif($QUERY_STRING eq "refresh" && $PAGE ne ""){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?refresh		Refresh
	if(-f "$PAGE.txt"){
		$rebuild = 1;
	}else{
		my $msg_id = has_write_access() ?
			"create_page" : "page_not_found";
		exit_message(get_msg($msg_id, $PAGE));
	}
}elsif($QUERY_STRING =~ m/^diff(?:=(-?[0-9]+))?$/){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?diff		Diff current and previous version
# u.cgi/PAGE?diff=([0-9]+)	Diff current and \1 version
# u.cgi/PAGE?diff=-([0-9]+)	Diff current and current-\1 version
	unless(-f "$PAGE.txt"){
		exit_message(get_msg("page_not_found", $PAGE));
	}

	my $current_version = get_version($PAGE);
	my $version = $1 > 0 ? $1 : $current_version + ($1 < 0 ? $1 : -1);

	if($version >= $current_version || $version <= 0){
		exit_message(get_msg("current_version", $PAGE, $current_version))
	}

	my $title = get_msg("diff_title", $PAGE, $version, $current_version);
	local $TITLE = $title;

	local *FH;
	open FH, "$PAGE.txt"; local $/ = undef;
	my $current_text = <FH>;
	close FH;

	my $text = $current_text;
	open FH, "$PAGE.txt.v"; local $/ = "\x00\n";
	while(<FH>){
		m/^([0-9]+):.*?\n(.*)\x00\n$/s;
		$text = patch($text, $2);
		last if($version == $1);
	}
	close FH;

	print_header();
	print qq(<div id="diff">\n<h1>$title</h1>\n);

	my @line0 = split /\n/, $text, -1;
	my @line1 = split /\n/, $current_text, -1;
	my ($s, @delta) = lcs(\@line0, \@line1);
	my $m = $s;
	my $n;
	for($n=0; $n<$s; $n++){
		$_ = $line1[$n];
		s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
		print qq(<div class="diff_unchanged">= $_</div>\n);
	}
	eval "use Encode;";
	my $encode = $@ ? 0 : 1;
	for(my $i=0; $i<=$#delta; $i++,$m++,$n++){
		my ($x, $y) = split /,/, $delta[$i];
		if($x > $m && $y > $n){
			for(; $m<$x&&$n<$y; $m++,$n++){
				print qq(<div class="diff_modified">* );
				my $l0 = $line0[$m];
				my $l1 = $line1[$n];
				if($encode){
					$l0 = Encode::decode($CHARSET, $l0);
					$l1 = Encode::decode($CHARSET, $l1);
				}
				my @l0 = split //, $l0, -1;
				my @l1 = split //, $l1, -1;
				my ($is, @idelta) = lcs(\@l0, \@l1);
				my $im = $is;
				my $in;
				for($in=0; $in<$is; $in++){
					$_ = $l1[$in];
					s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
					print;
				}
				for(my $ii=0; $ii<=$#idelta; $ii++,$im++,$in++){
					my ($ix, $iy) = split /,/, $idelta[$ii];
					if($ix > $im){
						print qq(<span class="diff_modified_deleted">);
						$_ = "";
						for(; $im<$ix; $im++){
							$_ .= $l0[$im];
						}
						s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
						print qq($_</span>);
					}
					if($iy > $in){
						print qq(<span class="diff_modified_added">);
						$_ = "";
						for(; $in<$iy; $in++){
							$_ .= $l1[$in];
						}
						s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
						print qq($_</span>);
					}
					if($in <= $#l1){
						$_ = $l1[$in];
						s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
						print;
					}
				}
				for(; $in<=$#l1; $in++){
					$_ = $l1[$in];
					s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
					print;
				}
				print qq(</div>\n);
			}
		}
		if($x > $m){
			for(; $m<$x; $m++){
				$_ = $line0[$m];
				s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
				print qq(<div class="diff_deleted">- $_</div>\n);
			}
		}
		if($y > $n){
			for(; $n<$y; $n++){
				$_ = $line1[$n];
				s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
				print qq(<div class="diff_added">+ $_</div>\n);
			}
		}
		if($n <= $#line1){
			$_ = $line1[$n];
			s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
			print qq(<div class="diff_unchanged">= $_</div>\n);
		}
	}
	for(; $n<=$#line1; $n++){
		$_ = $line1[$n];
		s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
		print qq(<div class="diff_unchanged">= $_</div>\n);
	}

	print qq(</div>\n);
	print_footer();
	exit;
}elsif($QUERY_STRING =~ m/^ls(?:[&=].+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?ls			List all pages in alphabetical order
# u.cgi?ls=az			List all pages in alphabetical order
# u.cgi?ls=za			List all pages in reverse order
# u.cgi?ls=taz			List all pages in alphabetical order of titles
# u.cgi?ls=tza			List all pages in reverse order of titles
# u.cgi?ls=rc			Recent changes
# u.cgi?ls=oc			Old changes
# u.cgi?ls&n=([0-9]+)		List only \1 pages in alphabetical order
# u.cgi?ls&title=1		Print page titles instead of page names
# u.cgi?ls&glob=GLOB		List all GLOB pages in alphabetical order
	my %var = get_var();
	my ($msg_id, $title);
	if($var{glob} eq ""){
		$msg_id = $var{ls} eq "rc" ? "recent_changes_title" :
			($var{ls} eq "oc" ? "old_changes_title" :
			($var{ls} eq "za" ? "all_pages_reversed_title" :
			"all_pages_title"));
		$title = get_msg($msg_id);
	}else{
		$msg_id = $var{ls} eq "rc" ? "recent_changes_matching_title" :
			($var{ls} eq "oc" ? "old_changes_matching_title" :
			($var{ls} eq "za" ? "all_pages_reversed_matching_title" :
			"all_pages_matching_title"));
		$title = get_msg($msg_id, $var{glob});
	}
	my $glob = $var{glob} eq "" ? "*" : $var{glob};

	local $TITLE = $title;
	print_header();
	print qq(<div id="ls">\n<h1>$title</h1>\n);

	my $tls = $var{ls} eq "taz" || $var{ls} eq "tza" ? 1 : 0;
	my $roc = $var{ls} eq "rc" || $var{ls} eq "oc" ? 1 : 0;
	my $n = $var{n} eq "" ? 0 : $var{n};
	my $i = 0;
	my @list;
	foreach(<$glob.txt>){
		next if(substr($_,0,1) eq "." || index($_,"/") >= 0 || !-f $_);
		s/\.txt$//;
		my $page = $_;
		my $title = $page;
		my @t = localtime((stat "$page.txt")[9]);
		my $time = sprintf "%d-%02d-%02d %02d:%02d:%02d",
			$t[5]+1900, $t[4]+1, $t[3], $t[2], $t[1], $t[0];
		if($tls || $var{title} eq "1"){
			local *FH;
			if(open FH, "$page.html"){
				local $/ = undef;
				my $text = <FH>;
				close FH;
				$text =~ s#<(script|style).*?</\1>##sgi;
				if($text =~ m#<h1[^>]*>(.+?)</h1>#si){
					$_ = $1;
					s/<[^>]*>//g; s/[<>]//g;
					$title = $_;
				}
			}
		}
		if($roc){
			if($var{title} eq "1"){
				$list[$i++] = "$time\x00$title\x00$page";
			}else{
				$list[$i++] = "$time\x00$page\x00$title";
			}
		}elsif($tls){
			$list[$i++] = "$title\x00$page\x00$time";
		}else{
			$list[$i++] = "$page\x00$title\x00$time";
		}
	}
	@list = sort @list;
	@list = reverse @list
		if($var{ls} eq "rc" || $var{ls} eq "za" || $var{ls} eq "tza");
	$n = $i if($n > $i || !$n);
	$i = 0;
	foreach(@list){
		my ($page, $title, $time);
		m/^(.*)\x00(.*)\x00(.*)$/;
		if($roc){
			if($var{title} eq "1"){
				$page = $3;
				$title = $2;
			}else{
				$page = $2;
				$title = $3;
			}
			$time = $1;
		}else{
			if($tls){
				$page = $2;
				$title = $var{title} eq "1" ? $1 : $page;
			}else{
				$page = $1;
				$title = $2;
			}
			$time = $3;
		}
		print qq(<div><a href="$DOC_BASE/$page.html">$title</a> <span class="ls_time">$time</span></div>\n);
		last if(++$i == $n);
	}

	print qq(</div>\n);
	print_footer();
	exit;
}elsif($QUERY_STRING =~ m/^rss(?:[&=].+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?rss			RSS for recent 10 pages
# u.cgi?rss=([0-9]+)		RSS for recent \1 pages
# u.cgi?rss&glob=GLOB		RSS for recent 10 GLOB pages
	my %var = get_var();
	my $glob = $var{glob} eq "" ? "*" : $var{glob};

	my $t = time;
	my @g = gmtime $t;
	my @l = localtime $t;
	my $g = $g[5]*31536000+$g[4]*2592000+$g[3]*86400+$g[2]*3600+$g[1]*60+
		$g[0];
	my $l = $l[5]*31536000+$l[4]*2592000+$l[3]*86400+$l[2]*3600+$l[1]*60+
		$l[0];
	my $i = 0;
	my @list;
	foreach(<$glob.txt>){
		next if(substr($_,0,1) eq "." || index($_,"/") >= 0 || !-f $_);
		s/\.txt$//;
		my $t = (stat "$_.txt")[9];
		my @t = split / +/, scalar gmtime($t);
		$list[$i++] = sprintf "%d %s, %02d %s %d %s GMT %s",
			$t, $t[0], $t[2], $t[1], $t[4], $t[3], $_;
	}
	my $n = 10;
	$n = $1 if($var{rss} =~ m/^([0-9]+)$/);
	$n = $i if($n > $i || !$n);
	print <<EOT;
Content-Type: text/xml

<?xml version="1.0" encoding="$CHARSET"?>
<rss version="2.0">
<channel>
<title>$RSS_TITLE</title>
<link>$DOC_BASE</link>
<description>$RSS_DESCRIPTION</description>
EOT
	undef $/;
	$i = 0;
	foreach(reverse sort @list){
		my ($time, $page) = m/^[0-9]+ (.+? GMT) (.*)$/;
		local *FH;
		open FH, "$page.html";
		my $txt = <FH>;
		close FH;
		$txt =~ s/\r//g;
		$txt =~ s#^.*<body[^>]*>##si;
		$txt =~ s#</body>.*$##si;
		my $has_more = ($txt =~ s'<!-- #more -->.*$''s);
		$txt =~ s'<!-- # -->.*''g;
		my $title;
		if($txt =~ m#<h1[^>]*>(.+?)</h1>(.*)$#si){
			$title = $1;
			$txt = $2;
			$title =~ s/<[^>]*>//g;
			$title =~ s/&[^ ]*;/ /g;
			$title =~ s/[ \t\n]+/ /g;
			$title =~ s/^ //;
			$title =~ s/ $//;
		}else{
			$title = $page;
		}
		$txt =~ s#<(script|style).*?</\1>##sgi;
		$txt =~ s/<[^>]*>//g;
		$txt =~ s/&[^ ]*;/ /g;
		$txt =~ s/[ \t\n]+/ /g;
		$txt =~ s/^ //;
		$txt =~ s/ $//;
		if($txt =~ m/^((?:[^ ]+ ){20})/){
			$txt = "$1...";
		}elsif($has_more){
			$txt .= " ...";
		}
		print <<EOT;
<item>
<title>$title</title>
<link>$DOC_BASE/$page.html</link>
<description>$txt</description>
<pubDate>$time</pubDate>
</item>
EOT
		last if(++$i == $n);
	}
	print <<EOT;
</channel>
</rss>
EOT
	exit;
}elsif($QUERY_STRING =~ m/^search(?:[&=].+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?search=(.*)		Search using regular expressions
# u.cgi?search=(.*)&simple=1	Search using space separated words
# u.cgi?search=(.*)&icase=1	Case-insensitive search
# u.cgi?search=(.*)&link=1	Search for pages which link to \1 page
# u.cgi?search=(.*)&title=1	Print page titles instead of page names
# u.cgi?search=(.*)&nomatch=1	Don't print matches
# u.cgi?search=(.*)&glob=GLOB	Search GLOB pages
	my %var = get_var();
	if($var{search} eq ""){
		local $TITLE = get_msg("search_form_title");
		print_header();
		create_search_form(1);
		print_footer();
		exit;
	}

	my $glob = $var{glob} eq "" ? "*" : $var{glob};

	$_ = $var{search};
	if($var{simple} eq "1"){
		s/[<>\r]//g; s/[\t\n]/ /g; s/ +/ /g; s/^ //; s/ $//;
		$_ = quotemeta;
		s/\\ />/g;
		s/\\"([^"]*)\\"/\x01$1\x02/g;
		while(s/\x01([^\x02]*)>([^\x02]*)\x02/\x01$1 +$2\x02/g){}
		s/[\x01\x02]//g; s/\\"//g;
	}
	my @search = split />/;

	$_ = $var{search};
	s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
	my $query = $_;
	my $title;
	if($var{glob} eq ""){
		$title = get_msg("search_title", $query);
	}else{
		$title = get_msg("search_matching_title", $var{glob}, $query);
	}

	local $TITLE = $title;
	print_header();
	print qq(<div id="search">\n<h1>$title</h1>\n);

	foreach(<$glob.html>){
		next if(substr($_,0,1) eq "." || index($_,"/") >= 0 || !-f $_);
		s/\.html$//;
		my $page = $query = $_;
		local *FH;
		next unless(open FH, "$page.html");

		local $/ = undef;
		my $text = <FH>;
		close FH;

		$text =~ s#<(script|style).*?</\1>##sgi;
		if($var{title} eq "1" && $text =~ m#<h1[^>]*>(.+?)</h1>#si){
			$_ = $1;
			s/<[^>]*>//g; s/[<>]//g;
			$query = $_;
		}
		my ($i, $line, $search, $found, @found, @result);
		if($var{link} eq "1"){
			foreach(split /\n/, $text){
				$line = $_;
				$found = "";
				for($i=0; $i<=$#search; $i++){
					$search = $search[$i];
					$search = "(?i)$search"
						if($var{icase} eq "1");
					if($line =~ m#<[aA][ \t][^>]*(?:href|HREF)[ \t]*=[ \t]*"(?:$search)"[^>]*>[^<]+</[aA]>#){
						$found = $line if($found eq "");
						$found =~ s#<[aA][ \t][^>]*(?:href|HREF)[ \t]*=[ \t]*"(?:$search)"[^>]*>([^<]+)</[aA]>#\x01$1\x02#g;
						$found[$i] = 1;
					}
				}
				if($found ne ""){
					$_ = $found;
					s/<[^>]*>//g; s/<.*$//; s/^.*>//;
					push @result, $_;
				}
			}
		}else{
			$text =~ s/<[^>]*>//g; $text =~ s/[<>]//g;
			foreach(split /\n/, $text){
				$line = $_;
				$found = "";
				for($i=0; $i<=$#search; $i++){
					$search = $search[$i];
					$search = "(?i)$search"
						if($var{icase} eq "1");
					if($line =~ m#$search#){
						$found = $line if($found eq "");
						$found =~ s#($search)#\x01$1\x02#g;
						$found[$i] = 1;
					}
				}
				push @result, $found if($found ne "");
			}
		}
		for($i=0; $i<=$#search; $i++){
			last if(!$found[$i]);
		}
		next if($i <= $#search);
		if($var{nomatch} eq "1"){
			print qq(<div><a href="$DOC_BASE/$page.html">$query</a></div>\n);
			next;
		}
		foreach(@result){
			s#\x01#<span class="search_highlight">#g;
			s#\x02#</span>#g;
			print qq(<div><a href="$DOC_BASE/$page.html">$query</a>: $_</div>\n);
		}
	}

	print qq(</div>\n);
	print_footer();
	exit;
}elsif($QUERY_STRING =~ m/^comment(?:[&=].+)?$/){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?comment		Generate the comment form for PAGE
#				(id=comment, downward, rows=80, cols=6)
# u.cgi/PAGE?comment&direction=(up|down) Generate the comment form for PAGE
#				(id=comment, (up|down)ward, rows=80, cols=6)
# u.cgi/PAGE?comment&rows=([0-9]+) Generate the comment form for PAGE
#				(id=comment, downward, rows=\1, cols=6)
# u.cgi/PAGE?comment&cols=([0-9]+) Generate the comment form for PAGE
#				(id=comment, downward, rows=80, cols=\1)
# u.cgi/PAGE?comment=COMMENT	Generate the comment form for PAGE
#				(id=COMMENT, downward, rows=80, cols=6)
# u.cgi?comment&page=PAGE	Generate the comment form for PAGE
#				(id=comment, downward, rows=80, cols=6)
	my %var = get_var();
	if($REQUEST_METHOD eq "GET"){
		$PAGE = $var{page} if($var{page} ne "");
		if($PAGE eq ""){
			exit_message(get_msg("specify_comment_page"));
		}elsif(!-f "$PAGE.txt"){
			exit_message(get_msg("page_not_found", $PAGE));
		}

		local $TITLE = get_msg("comment_form_title");
		print_header();
		create_comment_form(1, $PAGE, $var{comment}, $var{direction},
			$var{rows}, $var{cols});
		print_footer();
		exit;
	}
	exit unless(verify_input("comment", \%var));

	$PAGE = $var{page};
	unless(-f "$PAGE.txt"){
		exit_message(get_msg("page_not_found", $PAGE));
	}

	$var{text} =~ s/$/ /mg;

	lock_file("$PAGE.txt");
	my $TEXT = "";
	my $time = scalar localtime;
	my $added = 0;
	local *FH;
	if(open FH, "$PAGE.txt"){
		while(<FH>){
			if(m/^#$var{comment}$/){
				if($var{direction} eq "up"){
					$TEXT .= "$_# $time\n$var{text}\n\n";
				}else{
					$TEXT .= "# $time\n$var{text}\n\n$_";
				}
				$added = 1;
			}else{
				$TEXT .= $_;
			}
		}
		close FH;
	}
	unless($added){
		unlock_file("$PAGE.txt");
		exit_message(get_msg("comment_tag_not_found", "#$var{comment}"));
	}
	save($PAGE, $TEXT);
	unlock_file("$PAGE.txt");
}elsif($QUERY_STRING ne "delete" && $FILE ne ""){
#-------------------------------------------------------------------------------
# u.cgi/PAGE/FILE		Show/download PAGE/FILE
	exit_redirect("$DOC_BASE/$PAGE/$FILE?$QUERY_STRING");
}elsif($QUERY_STRING =~ m/^wiki/){
#-------------------------------------------------------------------------------
# uniqkiwiki
	unless(has_write_access()){
		my $msg_id;
		if($wiki){
			if(-f "$PAGE.txt"){
				$msg_id = "not_allowed_to_edit_wiki_page";
			}else{
				$msg_id = "not_allowed_to_create_wiki_page";
			}
		}else{
			if(-f "$PAGE.txt"){
				$msg_id = "not_wiki_page";
			}else{
				$msg_id = "not_allowed_to_create_nonwiki_page";
			}
		}
		exit_message(get_msg($msg_id, $PAGE));
	}
if($REQUEST_METHOD eq "GET"){
	local *FH;
	local $TITLE = $PAGE;
	local $TEXT;
	if($QUERY_STRING eq "wikiedit"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?wikiedit		Edit wiki PAGE
		$TEXT = "";
		if(-f "$PAGE.txt"){
			open FH, "$PAGE.txt"; local $/ = undef;
			$TEXT = <FH>;
			close FH;
			chomp $TEXT;
			if("#!wiki\n" ne substr $TEXT, 0, 7){
				exit_message(get_msg("internal_errors"));
			}

			$TEXT = substr $TEXT, 7;
			$TEXT =~ s/&/&amp;/g;
			$TEXT =~ s/</&lt;/g;
			$TEXT =~ s/>/&gt;/g;
		}
	}elsif($QUERY_STRING =~ m/^wikieditback(?:=([0-9]+))?$/){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?wikieditback	Edit the current-1 version of wiki PAGE
# u.cgi/PAGE?wikieditback=([0-9]+) Edit the current-\1 version of wiki PAGE
		unless(-f "$PAGE.txt"){
			exit_message(get_msg("page_not_found", $PAGE));
		}

		my $version = get_version($PAGE);
		my $backversion = $version - ($1 eq ""?1:$1);

		open FH, "$PAGE.txt"; local $/ = undef;
		$TEXT = <FH>;
		close FH;
		if("#!wiki\n" ne substr $TEXT, 0, 7){
			exit_message(get_msg("internal_errors"));
		}

		if($backversion >= $version || $backversion <= 0){
			close FH;
			exit_message(get_msg("current_version", $PAGE, $version));
		}

		open FH, "$PAGE.txt.v"; local $/ = "\x00\n";
		while(<FH>){
			m/^([0-9]+):.*?\n(.*)\x00\n$/s;
			$TEXT = patch($TEXT, $2);
			last if($backversion == $1);
		}
		close FH;
		if("#!wiki\n" ne substr $TEXT, 0, 7){
			# Previous version was not a wiki page
			exit_message(get_msg("not_wiki_page", $PAGE));
		}

		$TEXT = substr $TEXT, 7;
		$TEXT =~ s/&/&amp;/g;
		$TEXT =~ s/</&lt;/g;
		$TEXT =~ s/>/&gt;/g;
		chomp $TEXT;
	}else{
		exit;
	}

	local $VERSION = get_version($PAGE) + 1;
	print_wikiedit();
	exit;
}elsif($REQUEST_METHOD eq "POST"){
	my %var = get_var();
	exit unless(verify_input($QUERY_STRING, \%var));

	local *FH;
	my $t = time;
	if($QUERY_STRING eq "wikiupload"){
#-------------------------------------------------------------------------------
# Wiki upload
		exit if($WIKI_UPLOAD eq "" || !-f "$PAGE.txt" ||
			$var{file} eq "" || $var{file} !~ m/$WIKI_UPLOAD/oi);

		open FH, "$PAGE.txt";
		if(<FH> ne "#!wiki\n"){
			close FH;
			exit_message(get_msg("internal_errors"));
		}
		close FH;

		mkdir $PAGE, 0755 if(!-d $PAGE);
		open FH, ">$PAGE/$t.$var{file}";
		print FH $var{"file="};
		close FH;
		chmod 0755, "$PAGE/$t.$var{file}" if($HOSTING eq "awardspace");

		(my $f = $var{file}) =~ s/ /%20/g;
		exit_message(get_msg("file_uploaded", $var{file}).
				qq(\n<pre id="file_link_example">).
				get_msg("file_link_example",
				"[[$PAGE/$t.$f|$var{file}]]").qq(</pre>\n));
	}
	if(-f "$PAGE.txt"){
		open FH, "$PAGE.txt";
		if(<FH> ne "#!wiki\n"){
			close FH;
			exit_message(get_msg("internal_errors"));
		}
		close FH;
	}

	local $VERSION = $var{version};
	local $TEXT = $var{text};
	if($VERSION != get_version($PAGE) + 1){
		print_updated();
		exit;
	}
	if($var{file} ne "" && $var{file} =~ m/$WIKI_UPLOAD/oi){
		mkdir $PAGE, 0755 if(!-d $PAGE);
		open FH, ">$PAGE/$t.$var{file}";
		print FH $var{"file="};
		close FH;
		chmod 0755, "$PAGE/$t.$var{file}" if($HOSTING eq "awardspace");
		if($var{preview} eq ""){
			(my $f = $var{file}) =~ s/ /%20/g;
			$TEXT .= "\n[$PAGE/$t.$f $var{file}]";
		}
	}
	if($var{preview} ne ""){
		my $uploaded;
		if($var{file} ne "" && -f "$PAGE/$t.$var{file}"){
			(my $f = $var{file}) =~ s/ /%20/g;
			$uploaded = get_msg("file_uploaded", $var{file}).
				qq(\n<pre id="file_link_example">).
				get_msg("file_link_example",
					"[[$PAGE/$t.$f|$var{file}]]").
				qq(</pre>\n);
		}

		preview($PAGE, $TEXT, $uploaded, 1);
		exit;
	}

	lock_file("$PAGE.txt");
	save($PAGE, "#!wiki\n$TEXT\n");
	unlock_file("$PAGE.txt");
}
}elsif($QUERY_STRING eq "css"){
	print_css(2);
	exit;
}elsif(!$ADMIN){
	exit_message(get_msg("no_admin_actions_allowed"));
################################################################################
# Admin actions
}elsif($QUERY_STRING eq "admin"){
#-------------------------------------------------------------------------------
# u.cgi?admin			Admin page
# u.cgi/PAGE?admin		Admin page
	print_admin();
	exit;
}elsif($QUERY_STRING eq "user"){
#-------------------------------------------------------------------------------
# u.cgi?user			User management
# u.cgi/PAGE?user		User management
	my %var = get_var();
	if($var{mode} ne "add" && $var{mode} ne "block" &&
		$var{mode} ne "unblock" && $var{mode} ne "delete" &&
		$var{mode} ne "update"){
		exit_message(get_msg("invalid_user_management_mode", $var{mode}));
	}
	if($var{id} eq ""){
		exit_message(get_msg("enter_user_id"));
	}
	if(!is_user_id($var{id})){
		exit_message(get_msg("check_user_id"));
	}
	if($var{pw} ne $var{pw2}){
		exit_message(get_msg("confirm_password"));
	}

	if($var{mode} eq "add"){
		if($var{email_address} eq ""){
			exit_message(get_msg("enter_email_address"));
		}
		if(!is_email_address($var{email_address})){
			exit_message(get_msg("invalid_email_address",
					$var{email_address}));
		}
		if($var{pw} ne ""){
			exit_message(get_msg("leave_password_blank"));
		}
	}elsif($var{mode} eq "block" || $var{mode} eq "unblock" ||
		$var{mode} eq "delete"){
		if($var{email_address} ne ""){
			exit_message(get_msg("leave_email_address_blank"));
		}
		if($var{pw} ne ""){
			exit_message(get_msg("leave_password_blank"));
		}
	}else{
		my $len = length($var{pw});
		if($len > 0 && !is_password($var{pw})){
			exit_message(get_msg("check_password_requirements"));
		}
		if($len == 0 && $var{email_address} eq "" && $var{admin} ne "yes" &&
			$var{admin} ne "no"){
			exit_message(get_msg("enter_user_info_to_update"));
		}
	}

	my $new_pw = "";
	my $updated = 0;
	my $reset_hash = "";

	if(-f $PW){
		local *FH;
		open FH, $PW;
		while(<FH>){
			if(m/^$var{id}:/){
				$updated = 1;

				# Delete user
				next if($var{mode} eq "delete");

				if($var{mode} eq "add"){
					close FH;
					exit_message(get_msg("user_already_exists", $var{id}));
				}

				# Update user information
				my @items = split /:/;
				if($var{mode} eq "block"){
					if($items[1] eq ""){
						exit_message(get_msg("user_already_blocked", $var{id}));
					}
					$_ = "$var{id}:blocked:$items[2]:$items[3]:\n";
				}elsif($var{mode} eq "unblock"){
					if($items[1] ne ""){
						exit_message(get_msg("user_already_unblocked", $var{id}));
					}
					$reset_hash = generate_set_password_hash($var{id});
					$_ = "$var{id}:reset:$items[2]:$items[3]:$reset_hash\n";
				}elsif($var{mode} eq "update"){
					my $pw = $var{pw} ne "" ? hash_password($var{id}, $var{pw}) : $items[1];
					my $group = $var{admin} eq "yes" ? "admin" : ($var{admin} eq "no" ? "user" : $items[2]);
					my $email_address = $var{email_address} ne "" ? $var{email_address} : $items[3];
					my $reset_hash = $items[4];
					# new line from $items[4]
					my $userline = "$var{id}:$pw:$group:$email_address:$reset_hash";
					if($userline eq $_){
						exit_message(get_msg("enter_user_info_to_update", $var{id}));
					}
					$_ = $userline;
				}
			}
			if($var{mode} eq "add" && m/:$var{email_address}:[^:]*$/){
				close FH;
				exit_message(get_msg("email_address_already_registered", $var{email_address}));
			}
			$new_pw .= $_;
		}
		close FH;
	}else{
		my @items = split /:/, $adminpw;
		if($var{id} eq $items[0]){
			$updated = 1;

			if($var{mode} eq "delete"){
				exit_message(get_msg("only_user_cannot_be_deleted", $var{id}));
			}elsif($var{mode} eq "block"){
				exit_message(get_msg("only_user_cannot_be_blocked", $var{id}));
			}elsif($var{mode} eq "unblock"){
				exit_message(get_msg("only_user_cannot_be_unblocked", $var{id}));
			}elsif($var{mode} eq "update"){
				my $pw = $var{pw} ne "" ? hash_password($var{id}, $var{pw}) : $items[1];
				my $group = $var{admin} eq "yes" ? "admin" : ($var{admin} eq "no" ? "user" : $items[2]);
				my $email_address = $var{email_address} ne "" ? $var{email_address} : $items[3];
				my $reset_hash = $items[4];
				# new line from $items[4]
				my $userline = "$var{id}:$pw:$group:$email_address:$reset_hash";
				if($userline eq $adminpw){
					exit_message(get_msg("enter_user_info_to_update", $var{id}));
				}
				$new_pw = "$userline\n";
			}
		}
	}

	if(!$updated && $var{mode} ne "add"){
		exit_message(get_msg("user_not_found", $var{id}));
	}

	# Add a new user if user was not found
	if($var{mode} eq "add"){
		$updated = 1;
		$reset_hash = generate_set_password_hash($var{id});
		my $group = $var{admin} eq "yes" ? "admin" : "user";
		$new_pw .= "$var{id}:reset:$group:$var{email_address}:$reset_hash\n";
	}

	if($reset_hash){
		my $link = "$HTTP_BASE$SCRIPT_NAME/$PAGE?reset_pw=$reset_hash";
		my $subject;
		my $text;
		if($var{mode} eq "add"){
			$subject = get_msg("new_user_email_subject", $DOC_BASE);
			$text = get_msg("new_user_email_text", $var{id}, $DOC_BASE, $link, $SET_PASSWORD_TIMEOUT);
		}else{
			$subject = get_msg("unblocked_user_email_subject", $DOC_BASE);
			$text = get_msg("unblocked_user_email_text", $var{id}, $DOC_BASE, $link, $SET_PASSWORD_TIMEOUT);
		}
		if(!send_email($var{email_address}, $subject, $text)){
			exit_message(get_msg("email_notification_failed",
					$var{id}, $var{email_address}));
		}
	}

	if($updated){
		lock_file($PW);
		open FH, ">$PW";
		print FH $new_pw;
		close FH;
		unlock_file($PW);
	}

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?admin");
}elsif($insecure_pw){
#-------------------------------------------------------------------------------
# Admin password is still temporary. No admin actions are allowed other than
# changing the password.
	exit_message(get_msg("change_admin_password"));
}elsif($QUERY_STRING eq "install_pw"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?install_pw		Install the password file, but don't overwrite
	write_pw();
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "install_cfg"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?install_cfg	Install the config file, but don't overwrite
	process_cfg(1);
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "install_msg"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?install_msg	Install the message file, but don't overwrite
	process_msg(1);
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "install_tpl"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?install_tpl	Install the template files, but don't overwrite
	if($TPL ne ""){
		mkdir $TPL, 0755 unless(-d $TPL);
		print_header(1);
		print_footer(1);
		print_login(1);
		print_admin(1);
		print_message(1);
		print_view(1);
		print_edit(1);
		print_updated(1);
		print_wikiview(1);
		print_wikiedit(1);
		print_css(1);
	}
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "backup"){
#-------------------------------------------------------------------------------
# u.cgi?backup			Backup all pages
# u.cgi/PAGE?backup		Backup PAGE
	backup($PAGE);
	exit;
}elsif($QUERY_STRING eq "restore"){
#-------------------------------------------------------------------------------
# u.cgi?restore			Restore
# u.cgi/PAGE?restore		Restore
	restore();
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?admin");
}elsif($QUERY_STRING =~ m/^refresh(?:&.+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?refresh			Refresh all
# u.cgi?refresh&glob=GLOB	Refresh GLOB pages
	my %var = get_var();
	my $glob = $var{glob};
	my $_begin_parsing = $begin_parsing;
	my $_parse_line = $parse_line;
	my $_end_parsing = $end_parsing;
	my $title = $glob eq "" ? get_msg("refresh_title") :
		get_msg("refresh_matching_title", $glob);

	local $TITLE = $title;
	print_header();
	print qq(<div id="ls">\n<h1>$title</h1>\n);
	foreach($glob eq "" ? (<.*.txt>, <*.txt>) : <$glob.txt>){
		next if(index($_, "/") >= 0 || !-f $_);
		s/\.txt$//;
		$PAGE = $_;
		$begin_parsing = $_begin_parsing;
		$parse_line = $_parse_line;
		$end_parsing = $_end_parsing;
		make_html($PAGE);
		print qq(<div><a href="$PAGE.html">$PAGE</a></div>\n);
	}
	print qq(</div>\n);
	print_footer();
	exit;
}elsif($PAGE eq ""){
#-------------------------------------------------------------------------------
# u.cgi?ACTION			Index page
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/index");
}elsif($QUERY_STRING eq "upload"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?upload		Upload PAGE/FILE
	my %var = get_var();
	exit unless(verify_input("upload", \%var));

	if($var{file} ne ""){
		local *FH;
		mkdir $PAGE, 0755 if(!-d $PAGE);
		open FH, ">$PAGE/$var{file}";
		print FH $var{"file="};
		close FH;
		chmod 0755, "$PAGE/$var{file}" if($HOSTING eq "awardspace");
		$rebuild = 1;
	}
}elsif($QUERY_STRING eq "delete" && $FILE ne ""){
#-------------------------------------------------------------------------------
# u.cgi/PAGE/FILE?delete	Delete PAGE/FILE
	my $dir = "";
	if(unlink "$PAGE/$FILE"){
		$dir = "$PAGE/$FILE"; $dir =~ s#/[^/]+$##;
	}elsif(-d "$PAGE/$FILE"){
		$dir = "$PAGE/$FILE";
	}
	if($dir ne ""){
		while(index($dir, "/") >= 0){
			rmdir $dir;
			$dir =~ s#/[^/]*$##;
		}
		rmdir $dir;
	}
	$rebuild = 1;
}elsif($QUERY_STRING =~ m/^edit(?:=(-?[0-9]+))?$/){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?edit		Create/edit PAGE
# u.cgi/PAGE?edit=([0-9]+)	Edit the version \1 of PAGE
# u.cgi/PAGE?edit=-([0-9]+)	Edit the current-\1 version of PAGE
	local *FH;
	local $TITLE = $PAGE;
	local ($VERSION, $TEXT);
	if($REQUEST_METHOD eq "GET"){
		$VERSION = get_version($PAGE);
		my $version = $1 > 0 ? $1 : $VERSION + $1;
		$TEXT = "";
		if(open FH, "$PAGE.txt"){
			local $/ = undef;
			$TEXT = <FH>;
			close FH;

			if($version > 0 && $version < $VERSION){
				open FH, "$PAGE.txt.v"; local $/ = "\x00\n";
				while(<FH>){
					m/^([0-9]+):.*?\n(.*)\x00\n$/s;
					$TEXT = patch($TEXT, $2);
					last if($version == $1);
				}
				close FH;
			}
		}
		$VERSION++;
		if($TEXT ne ""){
			$TEXT =~ s/&/&amp;/g;
			$TEXT =~ s/</&lt;/g;
			$TEXT =~ s/>/&gt;/g;
			chomp $TEXT;
		}
		print_edit();
		exit;
	}

	my %var = get_var();
	exit unless(verify_input("edit", \%var));

	$VERSION = $var{version};
	$TEXT = $var{text};
	if($VERSION != get_version($PAGE) + 1){
		print_updated();
		exit;
	}
	if($var{file} ne ""){
		mkdir $PAGE, 0755 if(!-d $PAGE);
		open FH, ">$PAGE/$var{file}";
		print FH $var{"file="};
		close FH;
		chmod 0755, "$PAGE/$var{file}" if($HOSTING eq "awardspace");
	}
	if($var{preview} ne ""){
		my $uploaded;
		if($var{file} ne "" && -f "$PAGE/$var{file}"){
			(my $f = $var{file}) =~ s/ /%20/g;
			$uploaded = get_msg("file_uploaded", $var{file}).
				qq(\n<pre id="file_link_example">).
				get_msg("file_link_example",
					"[[$PAGE/$f|$var{file}]]").qq(</pre>\n);
		}

		preview($PAGE, $TEXT, $uploaded, 0);
		exit;
	}
	lock_file("$PAGE.txt");
	save($PAGE, "$TEXT\n");
	unlock_file("$PAGE.txt");
}elsif($QUERY_STRING =~ m/^revert(?:=(-?[0-9]+))?$/){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?revert		Go back to the previous version of PAGE
# u.cgi/PAGE?revert=([0-9]+)	Go back to the \1 version of PAGE
# u.cgi/PAGE?revert=-([0-9]+)	Go back to the current-\1 version of PAGE
	unless(-f "$PAGE.txt"){
		exit_message(get_msg("page_not_found", $PAGE));
	}

	local *FH;
	lock_file("$PAGE.txt");
	my $current_version = get_version($PAGE);
	my $version = $1 > 0 ? $1 : $current_version + ($1 < 0 ? $1 : -1);
	if($version > 0 && $version < $current_version){
		open FH, "$PAGE.txt"; local $/ = undef;
		my $text = <FH>;
		close FH;
		open FH, "$PAGE.txt.v"; local $/ = "\x00\n";
		while(<FH>){
			m/^([0-9]+):.*?\n(.*)\x00\n$/s;
			$text = patch($text, $2);
			if($version == $1){
				$rebuild = 1;
				last;
			}
		}
		if($rebuild){
			local $/ = undef;
			my $txtv = <FH>;
			close FH;
			open FH, ">$PAGE.txt";
			print FH $text;
			close FH;
			if($txtv eq ""){
				unlink "$PAGE.txt.v";
			}else{
				open FH, ">$PAGE.txt.v";
				print FH $txtv;
				close FH;
			}
		}else{
			close FH;
		}
	}
	unlock_file("$PAGE.txt");
}elsif($QUERY_STRING eq "delete"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?delete		Delete PAGE
	unlink "$PAGE.txt", "$PAGE.txt.v", "$PAGE.html";
	rmrf($PAGE);
	$PAGE = "index";
}

#-------------------------------------------------------------------------------
# Rebuild, if requested, and redirect
make_html($PAGE) if($rebuild);

if($READ_ACCESS ne "open"){
	if($QUERY_STRING ne ""){
		exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
	}elsif(-f "$PAGE.html"){
		local *FH;
		start_html();
		open FH, "$PAGE.html";
		print <FH>;
		close FH;
	}
}else{
	exit_redirect("$DOC_BASE/$PAGE.html");
}
