#!/usr/bin/env perl
################################################################################
# Uniqki:	Unique Wiki <http://uniqki.isnew.info>
# Author:	Huidae Cho
# Since:	May 23, 2007
#
# Copyright (C) 2007-2008, 2010-2011, 2016, Huidae Cho <http://geni.isnew.info>
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

# Temporary admin user: admin, password: admin.  DO NOT CHANGE THIS VARIABLE.
my $tmp_adminpw = 'admin:7352327a53727a65613d7a4cb055d722c21f1a0f17ad676daccd4ad8bf728134c9ee739e5f51c9af822da15b69985908148c55b6fdea4bc0bcd5aff660a53db428a9898c12743c7d:admin:@:';
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

# HTTP server environment variables
use vars qw(
	$CFG
	$HTTPS $HTTP_COOKIE $HTTP_HOST $SERVER_NAME $SCRIPT_NAME $PATH_INFO
	$QUERY_STRING $REQUEST_METHOD $CONTENT_LENGTH
);

# Useful variables
use vars qw(
	$HTTP_BASE $DOC_BASE $CGI $PAGE $FILE $USER
);

# Template variables
use vars qw(
	$TITLE $TEXT $PREVIEW $VERSION $TIME $PASSWORD_RESET_TOKEN $MESSAGE
);

# Config and messages variables
use vars qw(
	$SITE_TITLE $SITE_DESCRIPTION $INDEX_PAGE $LANG $CHARSET $LOCALE
	$TIME_ZONE $TIME_FORMAT
	$SHARE_COOKIES
	$PASSWORD_FILE $SESSIONS_FILE $MESSAGES_FILE $TEMPLATE_DIRECTORY
	$PAGE_NAME_STYLE
	$INACTIVE_TIMEOUT $SET_PASSWORD_TIMEOUT $RESET_PASSWORD_TIMEOUT
	$EMAIL_ADDRESS $SMTP
	$READ_ACCESS $WRITE_ACCESS
	$HEADER_FILE $FOOTER_FILE
	$WIKI_HEADER_FILE $WIKI_FOOTER_FILE
	$WIKI_ALLOWED_PAGES $WIKI_ALLOWED_FILES

	%MESSAGES
);

# parse_file() global variables
use vars qw(
	$wiki $begin_parsing $parse_line $end_parsing
);

# parse_file() local variables
use vars qw(
	$text $protocol $protocol_char $protocol_punct $image_ext $block
	$re_i_start $re_i @re @re_sub $toc $notoc %h_i $h_top $h_prev $p
	$li_i @li @li_attr $pre $table
);

umask 022;

# hmac_sha1 routine for password hashing
eval "use Digest::HMAC_SHA1 qw(hmac_sha1);";
exit_message("perl_module_not_installed", "Digest::HMAC_SHA1") if($@);

if(!defined $ENV{GATEWAY_INTERFACE}){
	print "Please run this script from a web browser!\n";
	printf "my \$tmp_adminpw = 'admin:%s:admin:\@:';\n",
		hash_password("admin", "admin");
	exit;
}

################################################################################
# CGI variables
$CFG = $ENV{HTTP_U_CFG};
$HTTPS = $ENV{HTTPS};
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
# Supported URLs:
# u.cgi outside cgi-bin: $doc_root = ""
# * https?://host/~user/dir/u.cgi/page/path/to/file?query
#   * CGI: u.cgi
#   * DOC_BASE: https?://host/~user/dir
# u.cgi inside cgi-bin: $doc_root != ""
# * https?://host/~user/cgi-bin/u.cgi/page/path/to/file?query
#   * CGI: /~user/cgi-bin/u.cgi
#   * DOC_BASE: https?://host/~user/doc_root
# * HTTP_BASE: https?://host
# * PAGE: page
# * FILE: path/to/file
$CGI = $SCRIPT_NAME;
$HTTP_BASE = ($HTTPS eq "on" ? "https" : "http")."://$HTTP_HOST";
$DOC_BASE = "$HTTP_BASE$CGI"; $DOC_BASE =~ s#/[^/]*$##;
$PAGE = substr $PATH_INFO, 1; $PAGE =~ s#/.*$##;
$PAGE =~ s#\.(?:html|txt|txt\.v)$##;
$FILE = $PATH_INFO; $FILE =~ s#^/[^/]+##; $FILE =~ s#^/##;

################################################################################
# Awardspace.com free web hosting
my $hosting = "";
if(-d "/home/www/$SERVER_NAME"){
	$hosting = "awardspace";
	$_ = "/home/www/$SERVER_NAME$SCRIPT_NAME";
	s#/[^/]*$##;
	chdir $_;
}
if($doc_root eq ""){
	$CGI =~ s#^.*/##;
}else{
	($_ = $CGI) =~ s#/[^/]+$##;
	s#^/~[^/]+##;
	if($_ eq ""){
		chdir $doc_root;
	}else{
		s#^/##; s#[^/]+#..#g;
		chdir "$_/$doc_root";
	}
	$DOC_BASE = $HTTP_BASE.($CGI =~ m#(^/~[^/]+)# ? $1 : "")."/$doc_root";
}

################################################################################
# Config
process_cfg();
$INDEX_PAGE = "index" if($INDEX_PAGE eq "");
if($TIME_ZONE ne ""){
	if($TIME_ZONE =~ m/^gmt([+-])([0-9]+)$/i){
		$TIME_ZONE = "GMT".($1 eq "+" ? "-" : "+").$2;
	}
	$ENV{TIME_ZONE} = $TIME_ZONE;
}

eval "use POSIX qw(setlocale LC_ALL tzset strftime);";
my $use_posix = $@ ? 0 : 1;
if($use_posix){
	tzset() if($TIME_ZONE ne "");
	setlocale(LC_ALL(), $LOCALE) if($LOCALE ne "");
}

my $smtp_server = "";
my $smtp_port;
my $smtp_username;
my $smtp_password;
if($SMTP =~ m/^([a-z0-9.-]+\.[a-z]{2,}):([0-9]*):([^:]*):(.*)$/i){
	$smtp_server = $1;
	$smtp_port = $2;
	$smtp_username = $3;
	$smtp_password = $4;
}

my ($page_name_case, $page_name_spaces) = config_page_name_style();
my ($nonwiki_read_access, $wiki_read_access, $wiki_write_access) =
	config_read_write_access();

################################################################################
# Messages
process_msg();

################################################################################
# Initialization
$USER = "";
my $admin = 0;
my $header_printed = 0;
my $footer_printed = 0;
my $rebuild = 0;
my $insecure_pw = 1;
my $sessions_file = $SESSIONS_FILE eq "" ? ".sessions" : $SESSIONS_FILE;
my $debug_started = 0;
my $html_started = 0;
my %locked_files = ();
my $cookie_domain_path = get_cookie_domain_path();

################################################################################
# Non-user-replaceable subroutines
sub debug{
	my $msg = shift;
	unless($debug_started){
		$debug_started = 1;
		print "Content-Type: text/plain\n\n";
	}
	printf "%s\n", $msg;
}

sub format_time{
	my $time = shift;
	my $ftime;
	if($use_posix){
		$ftime = strftime($TIME_FORMAT, localtime $time);
	}else{
		$ftime = scalar localtime $time;
	}
	return $ftime;
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
	my $wiki_read_access = index($READ_ACCESS, ":") == -1 ?
		$nonwiki_read_access :
		($items[1] ne "open" && $items[1] ne "closed" ?
			"admin" : $items[1]);
	my $wiki_write_access = $WRITE_ACCESS ne "open" &&
		$WRITE_ACCESS ne "closed" ? "admin" : $WRITE_ACCESS;
	return ($nonwiki_read_access, $wiki_read_access, $wiki_write_access);
}

sub exit_redirect{
	printf "Location: %s\n\n", shift;
	exit;
}

sub exit_message{
	local $MESSAGE = get_msg(@_);
	(local $TITLE = $MESSAGE) =~ s/<[^>]*>//g;
	print_message();
	exit;
}

sub exit_text{
	print "Content-Type: text/plain\n\n";
	print shift;
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

sub unescape_comment{
	my $text = shift;
	$text =~ y/\x00//d;
	return $text;
}

sub escape_comment{
	my $text = shift;
	$text =~ s/^([#%])/\x00$1/mg;
	$text =~ s/{{(.*?)}}(?!})/{\x00{$1}\x00}/g;
	$text =~ s/^(---+)$/\x00$1/mg;
	$text =~ s/^\x00(---+)\n(.*?)\n\x00\1$/$1\n@{[unescape_comment($2)]}\n$1/smg;
	$text =~ s/\x00/''''/g;
	return $text;
}

sub escape_inline_syntax{
	my $code = shift;
	$code =~ s#([{"/*'_!\[-]|$protocol)#\x00$1#ogi;
	$code =~ s/\x00([&<>])/$1/g;
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
	return 1 if($admin);
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
	return 1 if($admin);
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
	my $file = $PASSWORD_FILE eq "" ? "u.pw" : $PASSWORD_FILE;
	unless(-f $file){
		local *FH;
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
# Site information
$SITE_TITLE = 'Uniqki: A Personal Wiki Builder';
$SITE_DESCRIPTION = 'A <a href="http://uniqki.isnew.info">Uniqki</a> site';

# Index page
$INDEX_PAGE = 'index';

# Language
$LANG = 'en';

# Character set
$CHARSET = 'utf-8';

# Locale: Setting this variable to an empty string uses the default locale.
$LOCALE = '';

# Set time zone if different from the system time
$TIME_ZONE = '';

# Time format interpreted by the POSIX::strftime function
$TIME_FORMAT = '%a %b %e %H:%M:%S %Y';

# Share cookies: [subdomains:][EMPTY|subpaths|all_paths]
# * subdomains: http://example.com/u.cgi shares cookies with
# 		http://www.example.com.
# * EMPTY: http://example.com/path1/u.cgi does not share cookies with
#	   http://example.com/u.cgi, http://example.com/path2/u.cgi, nor
#	   http://example.com/path1/subpath1/u.cgi.
# * subpaths: http://example.com/path1/u.cgi shares cookies with
# 	      http://example.com/path1/subpath1/u.cgi, but not with
# 	      http://example.com/u.cgi nor http://example.com/path2/u.cgi.
# * all_paths: http://example.com/path1/u.cgi shares cookies with
#	       http://example.com/u.cgi, http://example.com/path2/u.cgi, and
#	       http://example.com/path1/subpath1/u.cgi.
#
# It is possible to combine subdomains and one of EMPTY, subpaths, and
# all_paths.  For example,
# * subdomains:all_paths: http://example.com/path1/u.cgi shares cookies with
#			  http://www.example.com/u.cgi.
#
# An empty setting '' means that cookies are not shared with other subdomains
# nor paths.  Subdomains and specified paths have to use the password and
# sessions files in the current domain and path to share login sessions.
# Subpaths does not work with $doc_root because the script and document
# directories are different.
$SHARE_COOKIES = '';

# WARNING: Make sure to protect these files and directories from the user using
# the following directives in .htaccess:
# <Files ~ "(^u\.(cfg|pw|msg)|^\.sessions|\.(tpl|txt|txt\.v))$">
#	Deny from all
# </Files>

# Password file: The admin password can be embedded in the script as $adminpw.
$PASSWORD_FILE = 'u.pw';

# Sessions file: The default sessions file is .sessions.
$SESSIONS_FILE = '.sessions';

# Messages file: The default messages will be printed if missing.
$MESSAGES_FILE = 'u.msg';

# Template directory: The default template will be served by u.cgi if missing.
$TEMPLATE_DIRECTORY = 'u.tpl';

# Page name style: case[:hyphens|:underscores|:no_spaces]
# * lower_case (default): All lower case (e.g., page in a uniqki site)
# * upper_case: All upper case (e.g., PAGE IN A UNIQKI SITE)
# * mixed_case: No special handling of letter case (e.g., Page in a Uniqki site)
# * start_case: Start case (e.g., Page In A Uniqki Site)
# * lower_camel_case: Lower camel case (e.g., pageInAUniqkiSite)
# * upper_camel_case: Upper camel case (e.g., PageInAUniqkiSite)
#
# Optionally
# * hyphens (default): Replace a series of whitespaces with a hyphen
# * underscores: Replace a series of whitespaces with an underscore
# * no_spaces: Remove whitespaces.  The lower_camel_case and upper_camel_case
# 	       styles imply this option.  For example, upper_camel_case is the
# 	       same as start_case:no_spaces.
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
$PAGE_NAME_STYLE = 'lower_case:hyphens';

# Login session will be extended by this number of minutes whenever any action
# is taken by the user.
$INACTIVE_TIMEOUT = 24*60;

# Change password timeout in minutes
$SET_PASSWORD_TIMEOUT = 60;

# Reset password timeout in minutes
$RESET_PASSWORD_TIMEOUT = 1;

# Email address from which user notifications are sent: 'Your Name
# <you@example.com>' is not supported.  Enter your email address only as in
# 'you@example.com'.  Make sure to use single quotes instead of double quotes.
$EMAIL_ADDRESS = '';

# SMTP settings: If this variable is empty, email will be sent using sendmail.
# The format of this variable is 'server:port:username:password'.  The password
# may contain colons (:), but the username cannot.
$SMTP = '';

# Read access control
# * open: Opens both non-wiki and wiki pages to the public and anyone will be
# 	  able to read those pages with or without a login.
# * closed: Requires a login to perform any read actions including search, diff,
#	    etc.  In addition, the following directives in .htaccess will
#	    prevent direct access to *.html files, effectively making the
#	    entire site read-secured.
# * admin: Allows only admin users access to non-wiki and wiki pages.  The
#	   .htaccess directives are required.
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
$READ_ACCESS = 'open';

# Write access control
# * open: Allows anyone to edit or create wiki pages with or without a login.
# * closed: Requires a login to edit or create wiki pages.
# * admin: Requires admin rights to edit or create wiki pages.
#
# Creating new wiki pages also depends on $WIKI_ALLOWED_PAGES.  For security
# reasons, non-wiki pages are writable only by admin users and this variable
# cannot affect that behavior.
$WRITE_ACCESS = 'open';

# Header and footer files for the parser
$HEADER_FILE = '';
$FOOTER_FILE = '';

# Header and footer files for the wiki parser (#!wiki as the first line)
$WIKI_HEADER_FILE = '';
$WIKI_FOOTER_FILE = '';

# Regular expression for wiki page names that are allowed to be created by
# non-admin users
$WIKI_ALLOWED_PAGES = q();

# Regular expression for file names that are allowed to be uploaded by
# non-admin users to a wiki page
$WIKI_ALLOWED_FILES = q(\.(png|gif|jpg|jpeg|txt|zip)$);
EOT_UNIQKI
	my $file = $CFG eq "" ? "u.cfg" : $CFG;
	if($mode == 1){
		unless(-f $file){
			local *FH;
			open FH, ">$file";
			print FH $cfg;
			close FH;
		}
	}else{
		eval $cfg;
		do $file if(-f $file);
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
################################################################################
# Template messages: These messages don't support printf format specifiers such
# as %s because there is no way to pass arguments to these messages from the
# template.  However, the [[PAGE]] tag can be used to generate dynamic text.
powered_by_uniqki => q(Powered by <a href="http://uniqki.isnew.info">Uniqki</a>!),

username => q(Username),
password => q(Password),
logout_from_other_computers => q(Logout from other computers),
view => q(View),

manage_pages => q(Manage pages),
backup => q(Backup),
restore => q(Restore),

manage_users => q(Manage users),
add_user => q(Add user),
update_user => q(Update user),
block_user => q(Block user),
unblock_user => q(Unblock user),
delete_user => q(Delete user),
email_address => q(Email address),
non_admin => q(Non-admin),
admin => q(Admin),
dont_change => q(Don't change),
type_password_again => q(Type password again),
username_requirements => q(Username requirements: 4 or more letters (a-z, A-Z) and digits (0-9).),
password_requirements => q(Password requirements: 8 or more characters with at least one letter (a-z, A-Z), one digit (0-9), and one special character excluding spaces and tabs.),
leave_password_blank_for_email_notification => q(Leave the password field blank for an email notification with a temporary link for resetting the password.),

manage_myself => q(Manage myself),
update_myself => q(Update myself),
delete_myself => q(Delete myself),

forgot_password => q(Forgot password),
enter_username_or_email_address => q(Please enter a username or an email address.),
user_info_mismatch => q(User information mismatch!),
email_address_not_found => q(%s: Email address not found.),
user_blocked => q(%s: User blocked.),

reset_password => q(Reset password),
password_reset_token_expired => q(Password reset token expired.),
password_reset_token_still_valid => q(You still have a valid password reset token. Please refer to the last email notification.),
invalid_password_reset_token => q(Invalid password reset token.),
password_reset_token_not_found => q(Password reset token not found.),

refresh => q(Refresh),
edit => q(Edit),
index => q(Index),
loginout => q(Loginout),
login => q(Login),
logout => q(Logout),
diff => q(Diff),
backlinks => q(Backlinks),
xhtml => q(XHTML),
css => q(CSS),

preview => q(Preview),
save => q(Save),
upload => q(Upload),
cancel => q(Cancel),

page_updated => q([[PAGE]] updated!),
save_your_changes_and_read_latest_version => q(Please save your changes and read <a href="[[PAGE]].html">the latest version</a>!),

edit_page => q(Edit [[PAGE]]),
wikiedit_page => q(WikiEdit [[PAGE]]),

################################################################################
# Non-template messages: These messages support printf format specifiers such
# as %s, but [[...]] tags cannot be used.
internal_errors => q(Internal errors),
session_errors => q(Session errors),
perl_module_not_installed => q(%s: Perl module not installed.),

change_admin_password => q(The admin password cannot be the same as the temporary password. <a href="?manage_myself">Change your password.</a>),

read_secured => q(You are not allowed to read this page.),
login_not_allowed => q(Login is not allowed.),
login_failed => q(Login failed.),
admin_actions_not_allowed => q(Admin actions are not allowed. Please <a href="?login">login</a> first.),

cannot_add_yourself => q(You cannot add yourself.),
cannot_block_yourself => q(You cannot block yourself.),
cannot_unblock_yourself => q(You cannot unblock yourself.),
cannot_delete_yourself => q(You cannot delete yourself.),
cannot_delete_only_admin => q(You cannot delete yourself because you are the only admin.),
user_already_blocked => q(%s: User already blocked.),
user_already_unblocked => q(%s: User already unblocked.),
user_already_exists => q(%s: User already exists.),
email_address_already_registered => q(%s: Email address already registered.),
enter_user_info_to_update => q(%s: Please enter user information to update.),
user_not_found => q(%s: User not found.),

enter_username => q(Please enter a username to manage.),
check_username => q(Please enter a username that meets character requirements.),
enter_email_address => q(Please enter an email address.),
check_email_address => q(Please enter a valid email address.),
leave_email_address_blank => q(Please leave the email address blank.),
check_password => q(Please enter a password that meets the length and character requirements.),
confirm_password => q(Please confirm the password.),
leave_password_blank => q(Please leave the password blank.),

new_user_email_subject => q(%s: Registered),
new_user_email_text => q(Your username %s is registered at %s. Please set your password by visiting %s within %d minutes.),
unblocked_user_email_subject => q(%s: Unblocked),
unblocked_user_email_text => q(Your username %s is unblocked at %s. Please set your password by visiting %s within %d minutes.),
reset_password_email_subject => q(%s: Reset password),
reset_password_email_text => q(Please reset your password for username %s at %s by visiting %s within %d minutes.),
email_notification_failed => q(Email notification failed for user %s <%s>.),

page_not_found => q(%s: Page not found.),
create_page => q(%s: Page not found. <a href="?edit">Create this page.</a>),
not_wiki_page => q(%s: This page is not a wiki page.),
not_allowed_to_create_nonwiki_page => q(%s: You are not allowed to create this non-wiki page.),
not_allowed_to_edit_wiki_page => q(%s: You are not allowed to edit this wiki page.),
not_allowed_to_edit_wiki_page => q(%s: You are not allowed to edit this wiki page.),

recent_changes => q(Recent changes),
recent_changes_matching => q(Recent changes matching %s pattern),
old_changes => q(Old changes),
old_changes_matching => q(Old changes matching %s pattern),
all_pages => q(All pages),
all_pages_matching => q(All pages matching %s pattern),
all_pages_reversed => q(All pages in reversed order),
all_pages_reversed_matching => q(All pages matching %s pattern in reverse order),
refresh_pages => q(Refresh pages),
refresh_pages_matching => q(Refresh pages matching %s pattern),
search => q(Search for %s),
search_matching => q(Search %s for %s),
differences => q(Differences of page <a href="%s">%1$s</a> between versions %d and %d),

goto_form => q(Goto form),
goto_form_goto => q(Go to),
search_form => q(Search form),
search_form_search => q(Search),
search_form_simple => q(Simple),
search_form_link => q(Link),
search_form_ignore_case => q(Ignore case),
search_form_print_title => q(Print title),
search_form_no_match => q(No match),
comment_form => q(Comment form),
comment_form_write => q(Write),
specify_comment_page => q(Please specify a comment page.),
comment_tag_not_found => q(%s: Comment tag not found.),
invalid_comment_tag => q(%s: Invalid comment tag.),

current_version => q(The current version of page %s is %d.),
file_uploaded => q(%s: File uploaded. Copy and paste the link below:<pre id="file_link_example">[[%s|%1$s]]</pre>),

table_of_contents => q(Table of contents),
);
EOT_UNIQKI
	my $file = $MESSAGES_FILE eq "" ? "u.msg" : $MESSAGES_FILE;
	if($mode == 1){
		unless(-f $file){
			local *FH;
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

sub is_username{
	my $user = shift;
	my $len = length($user);
	return $len >= 4 && $len <= 64 && $user =~ m/^[a-zA-Z0-9]+$/;
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
	return $len == 64 && $session_id =~ m/^[a-zA-Z0-9]+$/;
}

sub is_password_reset_token_valid{
	my $reset_token = shift;
	if($reset_token !~ m/^[a-zA-Z0-9]{8}[0-9a-f]{40}\.([0-9]+)$/){
		return 0;
	}
	my $expires = $1;
	my $time = time;
	return $time < $expires;
}

#-------------------------------------------------------------------------------
# Default template
sub process_tpl_tag{
	my $tag = shift;
	local *FH;
	my $txt = "";

	open FH, ">", \$txt; my $fh = select FH;
	if($tag eq "HEADER"){
		print_header();
	}elsif($tag eq "FOOTER"){
		print_footer();
	}elsif($tag eq "EDIT"){
		print_edit();
	}elsif($tag eq "WIKIEDIT"){
		print_wikiedit();
	}elsif($tag =~ m/^[A-Z_]+$/){
		my @tags = qw(
			SITE_TITLE SITE_DESCRIPTION INDEX_PAGE TITLE LANG
			CHARSET PAGE VERSION TEXT DOC_BASE PREVIEW TIME CGI
			MESSAGE PASSWORD_RESET_TOKEN
		);
		my %hash;
		@hash{@tags} = undef;

		no strict;
		$txt = $$tag if(exists $hash{$tag});
	}elsif($tag =~ m/^[a-z_]+$/){
		$txt = get_msg($tag);
		$txt =~ s/\[\[PAGE\]\]/$PAGE/g;
	}
	close FH; select $fh;
	chomp $txt;

	return $txt;
}

sub process_tpl{
	# $mode=undef: print
	# $mode=1: write
	# $mode=2: print for CSS and JavaScript only
	my ($file, $mode, $tpl) = @_;
	my $path = "$TEMPLATE_DIRECTORY/$file";

	start_html() unless(defined $mode);
	if($mode == 2){
		if(".css" eq substr $file, -4){
			print "Content-Type: text/css\n\n";
		}elsif(".js" eq substr $file, -3){
			print "Content-Type: text/javascript\n\n";
		}
	}

	if($mode == 1){
		if(-d $TEMPLATE_DIRECTORY && !-f $path){
			local *FH;
			open FH, ">$path";
			print FH $tpl;
			close FH;
		}
		return;
	}elsif(-f $path){
		local *FH;
		open FH, $path; local $/ = undef;
		$tpl = <FH>;
		close FH;
	}

	$tpl =~ s/\[\[([A-Za-z_]*)\]\]/@{[process_tpl_tag($1)]}/g;
	print $tpl;
}

sub print_header{
	my $mode = shift;
	return if(!defined $mode && $header_printed);

	$header_printed = 1;
	process_tpl("header.tpl", $mode, <<'EOT_UNIQKI'
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="[[LANG]]">
<head>
<title>[[TITLE]]</title>
<meta charset="[[CHARSET]]" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<link rel="stylesheet" type="text/css" href="[[CGI]]?css" />
<link rel="alternate" type="application/rss+xml" title="[[recent_changes]]" href="[[CGI]]?rss" />
<script src="[[CGI]]/[[PAGE]]?js"></script>
</head>
<body>
<div id="container">
<div id="top">
<div id="site-title"><a href="[[DOC_BASE]]">[[SITE_TITLE]]</a></div>
<div id="site-description">[[SITE_DESCRIPTION]]</div>
</div>
<div id="main">
EOT_UNIQKI
	)
}

sub print_footer{
	my $mode = shift;
	return if(!defined $mode && $footer_printed);

	$footer_printed = 1;
	process_tpl("footer.tpl", $mode, <<'EOT_UNIQKI'
</div>
<div id="bottom">
<small><i>[[powered_by_uniqki]]</i></small>
</div>
</div>
</body>
</html>
EOT_UNIQKI
	)
}

sub print_login{
	process_tpl("login.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="login">
<h1>[[login]]</h1>
<form action="[[PAGE]]?login" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="[[password]]" />
<input type="checkbox" id="logout_others" name="logout_others" value="1" /> [[logout_from_other_computers]]
<input accesskey="l" type="submit" value="[[login]]" />
</div>
</form>
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_manage_pages{
	process_tpl("manage_pages.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="manage_pages">
<h1>[[manage_pages]]</h1>
<form action="?restore" method="post" enctype="multipart/form-data">
<div>
[[backup]]: <a href="[[CGI]]?backup">[[all_pages]]</a> .
<a href="?backup">[[PAGE]]</a>
<br />
[[restore]]: <input accesskey="f" type="file" id="file" name="file" />
<input accesskey="r" type="submit" value="[[restore]]" />
</div>
</form>
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a> .
<a accesskey="l" href="[[PAGE]]?logout">[[logout]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_manage_users{
	process_tpl("manage_users.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="manage_users">
<h1>[[manage_users]]</h1>
<p>[[username_requirements]]</p>
<p>[[password_requirements]] [[leave_password_blank_for_email_notification]]</p>

<h2>[[add_user]]</h2>
<form action="?add_user" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<input accesskey="e" type="text" id="email_address" name="email_address" placeholder="[[email_address]]" />
<br />
<input type="radio" id="admin" name="admin" value="no" /> [[non_admin]]
<input type="radio" id="admin" name="admin" value="yes" /> [[admin]]
<br />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="[[password]]" />
<input type="password" id="pw2" name="pw2" placeholder="[[type_password_again]]" />
<br />
<input type="submit" value="[[add_user]]" />
</div>
</form>

<h2>[[update_user]]</h2>
<form action="?update_user" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<input accesskey="e" type="text" id="email_address" name="email_address" placeholder="[[email_address]]" />
<br />
<input type="radio" id="admin" name="admin" value="no" /> [[non_admin]]
<input type="radio" id="admin" name="admin" value="yes" /> [[admin]]
<input type="radio" id="admin" name="admin" value="keep" /> [[dont_change]]
<br />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="[[password]]" />
<input type="password" id="pw2" name="pw2" placeholder="[[type_password_again]]" />
<br />
<input type="submit" value="[[update_user]]" />
</div>
</form>

<h2>[[block_user]]</h2>
<form action="?block_user" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<br />
<input type="submit" value="[[block_user]]" />
</div>
</form>

<h2>[[unblock_user]]</h2>
<form action="?unblock_user" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<br />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="[[password]]" />
<input type="password" id="pw2" name="pw2" placeholder="[[type_password_again]]" />
<br />
<input type="submit" value="[[unblock_user]]" />
</div>
</form>

<h2>[[delete_user]]</h2>
<form action="?delete_user" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<br />
<input type="submit" value="[[delete_user]]" />
</div>
</form>
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a> .
<a accesskey="l" href="[[PAGE]]?logout">[[logout]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_manage_myself{
	process_tpl("manage_myself.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="manage_myself">
<h1>[[manage_myself]]</h1>

<h2>[[update_myself]]</h2>
<p>[[password_requirements]]</p>
<form action="?update_myself" method="post">
<div>
<input accesskey="e" type="text" id="email_address" name="email_address" placeholder="[[email_address]]" />
<br />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="[[password]]" />
<input type="password" id="pw2" name="pw2" placeholder="[[type_password_again]]" />
<br />
<input type="submit" value="[[update_myself]]" />
</div>
</form>

<h2>[[delete_myself]]</h2>
<form action="?delete_myself" method="post">
<div>
<input type="submit" value="[[delete_myself]]" />
</div>
</form>
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a> .
<a accesskey="l" href="[[PAGE]]?logout">[[logout]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_forgot_password{
	process_tpl("forgot_password.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="forgot_password">
<h1>[[forgot_password]]</h1>
<form action="?forgot_password" method="post">
<div>
<input accesskey="u" type="text" id="user" name="user" placeholder="[[username]]" />
<input accesskey="e" type="text" id="email_address" name="email_address" placeholder="[[email_address]]" />
<br />
<input type="submit" value="[[forgot_password]]" />
</div>
</form>
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_reset_password{
	process_tpl("reset_password.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="reset_password">
<h1>[[reset_password]]</h1>
<p>[[password_requirements]]</p>
<form action="?reset_password" method="post">
<div>
<input type="hidden" id="reset_token" name="reset_token" value="[[PASSWORD_RESET_TOKEN]]" />
<input accesskey="p" type="password" id="pw" name="pw" placeholder="[[password]]" />
<input type="password" id="pw2" name="pw2" placeholder="[[type_password_again]]" />
<br />
<input type="submit" value="[[reset_password]]" />
</div>
</form>
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_message{
	process_tpl("message.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="message">
[[MESSAGE]]
</div>
<hr />
<div id="menu">
<span class="read-access"><a accesskey="v" href="[[PAGE]].html">[[view]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a> .
<a class="visitor" accesskey="l" href="[[PAGE]]?login">[[login]]</a>
<a class="user" accesskey="l" href="[[PAGE]]?logout">[[logout]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_view{
	# View templates are never served dynamically, so don't print a
	# content-type header
	$html_started = 1;
	process_tpl("view.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="view">
<!-- start text -->
[[TEXT]]
<!-- end text -->
</div>
<hr />
<div id="menu">
<a accesskey="r" href="[[CGI]]/[[PAGE]]?refresh">[[refresh]]</a> .
<span class="write-access"><a accesskey="e" href="[[CGI]]/[[PAGE]]?edit">[[edit]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a> .
<a class="visitor" accesskey="l" href="[[CGI]]/[[PAGE]]?login">[[login]]</a>
<a class="user" accesskey="l" href="[[CGI]]/[[PAGE]]?logout">[[logout]]</a>
</div>
<div id="timestamp">
[[TIME]] .
<a href="https://validator.w3.org/check?uri=referer">[[xhtml]]</a> .
<a href="https://jigsaw.w3.org/css-validator/check/referer">[[css]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_edit{
	process_tpl("edit.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="edit">
<h1>[[edit_page]]</h1>
<form action="[[PAGE]]?edit" method="post" enctype="multipart/form-data">
<div>
<input type="hidden" id="version" name="version" value="[[VERSION]]" />
<textarea accesskey="e" id="text" name="text" rows="24" cols="80">[[TEXT]]</textarea>
<br />
<input accesskey="p" type="submit" id="preview" name="preview" value="[[preview]]" />
<input accesskey="s" type="submit" id="save" name="save" value="[[save]]" /> .
[[upload]] <input accesskey="u" type="file" id="file" name="file" /> .
<a accesskey="c" href="[[PAGE]].html">[[cancel]]</a> .
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a>
</div>
</form>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_preview{
	process_tpl("preview.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="preview">
[[PREVIEW]]
</div>
[[EDIT]]
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_updated{
	process_tpl("updated.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="updated">
<h1>[[page_updated]]</h1>
[[save_your_changes_and_read_latest_version]]
<br />
<textarea accesskey="e" id="text" name="text" rows="24" cols="80">[[TEXT]]</textarea>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_wikiview{
	# View templates are never served dynamically, so don't print a
	# content-type header
	$html_started = 1;
	process_tpl("wikiview.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="wikiview">
<!-- start text -->
[[TEXT]]
<!-- end text -->
</div>
<div id="wikimenu">
<span class="write-access"><a accesskey="e" href="[[CGI]]/[[PAGE]]?wikiedit">[[edit]]</a> .</span>
<span class="read-access"><a accesskey="d" href="[[CGI]]/[[PAGE]]?diff=-1">[[diff]]</a> .
<a accesskey="l" href="[[CGI]]?search=[[PAGE]]%5C.html&amp;link=1">[[backlinks]]</a> .</span>
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a> .
<a class="visitor" accesskey="l" href="[[CGI]]/[[PAGE]]?login">[[login]]</a>
<a class="user" accesskey="l" href="[[CGI]]/[[PAGE]]?logout">[[logout]]</a>
</div>
<div id="timestamp">
[[TIME]] .
<a href="https://validator.w3.org/check?uri=referer">[[xhtml]]</a> .
<a href="https://jigsaw.w3.org/css-validator/check/referer">[[css]]</a>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_wikiedit{
	process_tpl("wikiedit.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="wikiedit">
<h1>[[wikiedit_page]]</h1>
<form action="[[PAGE]]?wikiedit" method="post" enctype="multipart/form-data">
<div>
<input type="hidden" id="version" name="version" value="[[VERSION]]" />
<textarea accesskey="e" id="text" name="text" rows="24" cols="80">[[TEXT]]</textarea><br />
<input accesskey="p" type="submit" id="preview" name="preview" value="[[preview]]" />
<input accesskey="s" type="submit" id="save" name="save" value="[[save]]" /> .
[[upload]] <input accesskey="u" type="file" id="file" name="file" /> .
<a accesskey="c" href="[[PAGE]].html">[[cancel]]</a> .
<a accesskey="i" href="[[INDEX_PAGE]].html">[[index]]</a>
</div>
</form>
</div>
[[FOOTER]]
EOT_UNIQKI
	)
}

sub print_wikipreview{
	process_tpl("wikipreview.tpl", shift, <<'EOT_UNIQKI'
[[HEADER]]
<div id="wikipreview">
[[PREVIEW]]
</div>
[[WIKIEDIT]]
[[FOOTER]]
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
	background-color:	#eeeeee;
	border:			1px solid #dddddd;
	overflow:		auto;
}
textarea {
	width:			100%;
}

/******************************************************************************/
#container {
	max-width:		960px;
	margin:			auto;
}
#top {
}
#site-title {
	font-weight:		bold;
	font-size:		120%;
}
#site-title a {
	color:			black;
	text-decoration:	none;
}
#site-description {
}
#main {
	background-color:	white;
	border:			1px solid #aaaaaa;
	padding:		10px;
	box-shadow:		5px 5px 5px #aaaaaa;
}
#bottom {
	text-align:		right;
}
#login {
}
#manage_pages {
}
#manage_users {
}
#manage_myself {
}
#forgot_password {
}
#reset_password {
}
#message {
}
#menu {
	display:		none;
}
#timestamp {
	padding-top:		2px;
	font-size:		smaller;
	font-style:		italic;
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
	padding:		5px 5px 0px 5px;
	display:		none;
}

/******************************************************************************/
#toc {
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

sub print_js{
	process_tpl("uniqki.js", shift, <<'EOT_UNIQKI'
/* http://developer.mozilla.org/en/docs/AJAX:Getting_Started */
function ajax_request(url, data, func){
	var xml_request = null;

	/* Create an XMLHTTP instance */
	if(window.XMLHttpRequest){ /* Mozilla, Safari, ... */
		xml_request = new XMLHttpRequest();
		if(xml_request.overrideMimeType){
			/* Some web servers return a non-standard mime type. */
			xml_request.overrideMimeType('text/xml');
		}
	}else
	if(window.ActiveXObject){ /* IE */
		try{
			xml_request = new ActiveXObject('Msxml2.XMLHTTP');
		}catch(e){
		try{
			xml_request = new ActiveXObject('Microsoft.XMLHTTP');
		}catch(e){}
		}
	}
	if(!xml_request){
		alert('Cannot create an XMLHTTP instance.');
		return;
	}

	/* This function has no arguments. */
	xml_request.onreadystatechange = function(){
		if(xml_request.readyState != 4)
			return;
		if(xml_request.status != 200)
			return;
		func(xml_request);
	}

	if(data == null)
		var method = 'GET';
	else{
		var method = 'POST';
		xml_request.setRequestHeader('Content-Type',
			'application/x-www-form-urlencoded');
	}

	/* xml_request.open(method, url, asynchronous) */
	xml_request.open(method, url, true);

	/* xml_request.send(POST data) */
	/* required even if the method is not POST. */
	xml_request.send(data);
}

/* http://forum.java.sun.com/thread.jspa?threadID=696590&tstart=105 */
function ajax_responseXML(xml_request){
	var xml = null;

	if(window.ActiveXObject){ /* IE */
		xml = document.createElement('div');
		xml.innerHTML = xml_request.responseText;

		/* Huidae Cho <http://geni.isnew.info> */
		xml.getElementById = function(id){
			for(var i = 0; i < this.childNodes.length; i++){
				if(id == this.childNodes[i].id)
					return this.childNodes[i];
			}
			return null;
		}
	}else
	if(window.XMLHttpRequest){
		xml = xml_request.responseXML;
	}

	return xml;
}

function process_menu(xml_request){
	var items = xml_request.responseText.split(':');
	var user = items[0];
	var admin = items[1];
	var has_read_access = items[2];
	var has_write_access = items[3];

	[].forEach.call(document.getElementsByClassName(
			user == '' ? 'user' : 'visitor'),
		function(el){
			el.parentNode.removeChild(el);
		});
	if(admin == 0)
		[].forEach.call(document.getElementsByClassName('admin'),
			function(el){
				el.parentNode.removeChild(el);
			});
	if(has_read_access == 0)
		[].forEach.call(document.getElementsByClassName('read-access'),
			function(el){
				el.parentNode.removeChild(el);
			});
	if(has_write_access == 0)
		[].forEach.call(document.getElementsByClassName('write-access'),
			function(el){
				el.parentNode.removeChild(el);
			});

	var menu = document.getElementById('menu');
	var wikimenu = document.getElementById('wikimenu');
	if(menu != null)
		menu.style.display = 'block';
	if(wikimenu != null)
		wikimenu.style.display = 'block';
}

ajax_request('[[CGI]]/[[PAGE]]?user_info', null, process_menu);
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
	my @line0 = split /\n/, $_[0], -1; $#line0--;
	my @line1 = split /\n/, $_[1], -1; $#line1--;
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
	my @line0 = split /\n/, $_[0], -1; $#line0--;
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
	my ($PAGE, $TEXT) = @_;

	my $version = 1;
	my $txtv;
	local *FH;

	if(-f "$PAGE.txt"){
		if(open FH, "$PAGE.txt.v"){
			my $line = <FH>;
			local $/ = undef;
			$txtv = $line.<FH>;
			close FH;
			my @items = split /:/, $line;
			$version = $items[0];
		}else{
			my $time = (stat "$PAGE.txt")[9];
			$txtv = "$version:?:$time\n";
		}
		open FH, "$PAGE.txt";
		local $/ = undef;
		my $text = <FH>;
		close FH;

		my $diff = diff($TEXT, $text);
		if($diff eq ""){
			$rebuild = 1;
			return;
		}

		$version++;
		my $time = time;
		$txtv = "$version:$USER:$time\n$diff\x00\n$txtv";
	}else{
		my $time = time;
		$txtv = "$version:$USER:$time\n";
	}

	open FH, ">$PAGE.txt.v";
	print FH $txtv;
	close FH;

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
		$version = $items[0];
		exit_message("internal_errors") unless(-f "$PAGE.txt");
	}elsif(-f "$PAGE.txt"){
		$version = 1;
	}
	return $version;
}

sub lock_file{
	my $file = shift;
	my $timeout = 60;
	my $i = 0;
	while(-f "$file.lock"){
		exit_message("internal_errors") if(++$i > $timeout);
		sleep 1;
	}
	$locked_files{$file} = 1;
	local *FH;
	exit_message("internal_errors") unless(open FH, ">$file.lock");
	close FH;
}

sub unlock_file{
	my $file = shift;
	unlink "$file.lock";
	delete $locked_files{$file};
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
	local $TIME = format_time((stat "$PAGE.txt")[9]);

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
	chmod 0755, "$PAGE.html" if($hosting eq "awardspace");
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

sub get_cookie_domain_path{
	(my $script_dir = $SCRIPT_NAME) =~ s#[^/]*$##;
	my $subdomains = 0;
	my $paths = "";
	foreach my $item (split /:/, $SHARE_COOKIES){
		if($item eq "subdomains"){
			$subdomains = 1;
		}elsif($item eq "subpaths" || $item eq "all_paths"){
			$paths = $item;
		}
	}
	return ($subdomains ? "domain=$HTTP_HOST; " : "").
		($paths eq "all_paths" ? "path=/" :
			($paths eq "subpaths" && $doc_root eq "" ?
				"path=$script_dir" : "path=$SCRIPT_NAME"));
}

sub set_cookie{
	my ($session_id, $expires) = @_;

	my @t = gmtime $expires;
	my @m = qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec);
	my @w = qw(Sun Mon Tue Wed Thu Fri Sat);
	my $expires = sprintf "%s, %02d-%s-%d %02d:%02d:%02d GMT",
		$w[$t[6]], $t[3], $m[$t[4]], $t[5]+1900, $t[2], $t[1], $t[0];

	print "Set-Cookie: uniqki=$session_id; $cookie_domain_path; ".
		"expires=$expires; secure; httponly\n";
}

sub clear_cookie{
	print "Set-Cookie: uniqki=; $cookie_domain_path; ".
		"expires=Tue, 01-Jan-1980 00:00:00 GMT; secure; httponly\n";
}

sub find_user_info{
	my $user = shift;
	local *FH;

	my $method = 0;
	# $method=0: No user found
	# $method=1: Use $PASSWORD_FILE
	# $method=2: Use $adminpw

	if($PASSWORD_FILE eq ""){
		# No password file is specified in u.cfg.  Since the password
		# file in the default config is u.pw, an empty $PASSWORD_FILE
		# was assigned by the user.
		if($adminpw eq $tmp_adminpw){
			# If $adminpw is still temporary, this situation can be
			# very dangerous because anyone can login using the
			# public temporary password.  Do not allow any login in
			# this case.
		}else{
			# If $adminpw has been changed, use this password.
			$method = 2;
		}
	}elsif(-f $PASSWORD_FILE){
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
		open FH, $PASSWORD_FILE;
		my @lines = grep /^$user:/, <FH>;
		close FH;

		if($#lines == 0){
			$userline = $lines[0];
			$userline =~ s/[\r\n]//;
		}
	}elsif($method == 2 &&
		"$user:" eq substr $adminpw, 0, length("$user:")){
		$userline = $adminpw;
	}
	return if($userline eq "");

	return split /:/, $userline;
}

sub find_user_info_by_email_address{
	my $email_address = shift;
	local *FH;

	my $method = 0;
	# $method=0: No user found
	# $method=1: Use $PASSWORD_FILE
	# $method=2: Use $adminpw

	if($PASSWORD_FILE eq ""){
		# No password file is specified in u.cfg.  Since the password
		# file in the default config is u.pw, an empty $PASSWORD_FILE
		# was assigned by the user.
		if($adminpw eq $tmp_adminpw){
			# If $adminpw is still temporary, this situation can be
			# very dangerous because anyone can login using the
			# public temporary password.  Do not allow any login in
			# this case.
		}else{
			# If $adminpw has been changed, use this password.
			$method = 2;
		}
	}elsif(-f $PASSWORD_FILE){
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

	(my $escaped_email_address = $email_address) =~ s/\./\\./g;

	my $userline = "";
	if($method == 1){
		open FH, $PASSWORD_FILE;
		my @lines = grep /:$escaped_email_address:[^:]*$/i, <FH>;
		close FH;

		if($#lines == 0){
			$userline = $lines[0];
			$userline =~ s/[\r\n]//;
		}
	}elsif($method == 2 && $adminpw =~ m/:$escaped_email_address:[^:]*$/i){
		$userline = $adminpw;
	}
	return if($userline eq "");

	return split /:/, $userline;
}

sub find_user_info_by_password_reset_token{
	my $reset_token = shift;
	local *FH;

	my $method = 0;
	# $method=0: No user found
	# $method=1: Use $PASSWORD_FILE
	# $method=2: Use $adminpw

	if($PASSWORD_FILE eq ""){
		# No password file is specified in u.cfg.  Since the password
		# file in the default config is u.pw, an empty $PASSWORD_FILE
		# was assigned by the user.
		if($adminpw eq $tmp_adminpw){
			# If $adminpw is still temporary, this situation can be
			# very dangerous because anyone can login using the
			# public temporary password.  Do not allow any login in
			# this case.
		}else{
			# If $adminpw has been changed, use this password.
			$method = 2;
		}
	}elsif(-f $PASSWORD_FILE){
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
	return if($method != 1);

	(my $escaped_reset_token = $reset_token) =~ s/\./\\./g;

	my $userline = "";
	open FH, $PASSWORD_FILE;
	my @lines = grep /:$escaped_reset_token$/, <FH>;
	close FH;

	if($#lines == 0){
		$userline = $lines[0];
		$userline =~ s/[\r\n]//;
	}
	return if($userline eq "");

	return split /:/, $userline;
}

sub authenticate_user{
	my ($user, $pw, $logout_others) = @_;
	local *FH;

	my $method = 0;
	# $method=0: Login not allowed
	# $method=1: Create $PASSWORD_FILE and force to change the password
	# $method=2: Use $PASSWORD_FILE
	# $method=3: Use $adminpw

	if($PASSWORD_FILE eq ""){
		# No password file is specified in u.cfg.  Since the password
		# file in the default config is u.pw, an empty $PASSWORD_FILE
		# was assigned by the user.
		if($adminpw eq $tmp_adminpw){
			# If $adminpw is still temporary, this situation can be
			# very dangerous because anyone can login using the
			# public temporary password.  Do not allow any login in
			# this case.
			exit_message("login_not_allowed");
		}else{
			# If $adminpw has been changed, use this password.
			$method = 3;
		}
	}elsif(-f $PASSWORD_FILE){
		# Use the password file
		$method = 2;
	}elsif($adminpw eq $tmp_adminpw){
		# Password file does not exist and $adminpw is temporary.  The
		# first run of u.cgi is this case.  Create the password file
		# only for the login action immediately before checking
		# credentials against the temporary password to avoid timing
		# attacks.
		if($QUERY_STRING eq "login"){
			open FH, ">$PASSWORD_FILE";
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

	my ($usr, $saved_pw, $group, $email_address, $reset_token) =
		find_user_info($user);
	if(!defined $usr || $saved_pw eq "blocked"){
		close_session();
		exit_message("login_failed");
	}

	my $salt = pack("H*", substr $saved_pw, 0, 16);
	if($saved_pw ne hash_password($user, $pw, $salt)){
		close_session();
		exit_message("login_failed");
	}

	# If admin password is not temporary, the password is secure.
	my $userpw = "$user:$saved_pw:";
	$insecure_pw = 0 if($userpw ne substr $tmp_adminpw, 0, length($userpw));

	clear_sessions($user) if($logout_others eq "1");
	start_session($user);

	if($method == 1){
		# Force to change the password
		exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_myself");
	}

	clear_password_reset_token($reset_token);

	$USER = $user;
	$admin = 1 if($group eq "admin");
}

sub find_session_info{
	my $session_id = shift;
	local *FH;

	return if(!-f $sessions_file || !is_session_id($session_id));

	open FH, $sessions_file;
	my @lines = grep /^$session_id:/, <FH>;
	close FH;
	return if($#lines == -1);

	return split /:/, $lines[0];
}

sub start_session{
	my $user = shift;
	my ($session_id, $expires) = generate_session_id($user);
	set_cookie($session_id, $expires);
}

sub renew_session{
	my $session_id = shift;

	my $expires = time + $INACTIVE_TIMEOUT * 60;
	my $new_sessions = "";
	my $renewed = 0;

	lock_file($sessions_file);
	local *FH;
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
		open FH, ">$sessions_file";
		print FH $new_sessions;
		close FH;
		set_cookie($session_id, $expires);
	}
	unlock_file($sessions_file);
}

sub close_session{
	clear_cookie();

	my $cookie = $HTTP_COOKIE; $cookie =~ s/; /\n/g;
	return unless($cookie =~ m/^uniqki=(.+)$/m);

	my $session_id = $1;
	return if(!-f $sessions_file || !is_session_id($session_id));

	my $new_sessions = "";
	my $deleted = 0;

	lock_file($sessions_file);
	local *FH;
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
		open FH, ">$sessions_file";
		print FH $new_sessions;
		close FH;
	}
	unlock_file($sessions_file);
}

sub clear_sessions{
	my $user = shift;

	unless(defined $user){
		clear_cookie();
		my $cookie = $HTTP_COOKIE; $cookie =~ s/; /\n/g;
		$cookie =~ m/^uniqki=(.+)$/m;
		my $session_id = $1;
		(my $sess, $user) = find_session_info($session_id);
	}
	return if(!-f $sessions_file || !is_username($user));

	my $new_sessions = "";
	my $deleted = 0;

	lock_file($sessions_file);
	local *FH;
	open FH, $sessions_file;
	while(<FH>){
		if(m/^[^:]*:$user:/){
			$deleted = 1;
			next;
		}
		$new_sessions .= $_;
	}
	close FH;

	if($deleted){
		open FH, ">$sessions_file";
		print FH $new_sessions;
		close FH;
	}
	unlock_file($sessions_file);
}

sub handle_session{
	my $cookie = $HTTP_COOKIE; $cookie =~ s/; /\n/g;
	unless($cookie =~ m/^uniqki=(.+)$/m){
		clear_cookie();
		return;
	}

	my $session_id = $1;
	my ($sess, $user, $status, $expires) = find_session_info($session_id);

	unless(defined $sess){
		clear_cookie();
		return;
	}
	if($status ne "active" || time > $expires){
		close_session();
		return;
	}
	my ($usr, $pw, $group, $email_address, $reset_token) =
		find_user_info($user);
	unless(defined $usr){
		close_session();
		return;
	}

	renew_session($session_id);

	# If admin password is not temporary, the password is secure.
	my $userpw = "$user:$pw:";
	$insecure_pw = 0 if($userpw ne substr $tmp_adminpw, 0, length($userpw));

	$USER = $user;
	$admin = 1 if($group eq "admin");
}

sub clear_password_reset_token{
	my $reset_token = shift;
	return unless(-f $PASSWORD_FILE);

	my $new_pw = "";
	my $cleared = 0;

	lock_file($PASSWORD_FILE);
	local *FH;
	open FH, $PASSWORD_FILE;
	while(<FH>){
		if(":$reset_token\n" eq substr $_,
			length($_) - length(":$reset_token\n")){
			my @items = split /:/;
			$cleared = 1;
			$_ = "$items[0]:$items[1]:$items[2]:$items[3]:\n";
		}
		$new_pw .= $_;
	}
	close FH;

	if($cleared){
		open FH, ">$PASSWORD_FILE";
		print FH $new_pw;
		close FH;
	}
	unlock_file($PASSWORD_FILE);
}

sub generate_random_string{
	my $len = shift;
	# http://www.perlmonks.org/?node_id=233023
	my @chars = ("a".."z", "A".."Z", "0".."9");
	my $str;
	$str .= $chars[rand @chars] for 1..$len;
	return $str;
}

sub generate_salt{
	# salt length: 8
	return generate_random_string(8);
}

sub generate_session_id{
	my $user = shift;
	my $session_id;
	my $i = 0;
	my $found;
	do{
		$session_id = generate_random_string(64);
		my @session = find_session_info($session_id);
		$found = defined $session[0] ? 1 : 0;
		$i++;
	}while($found && $i<10);

	exit_message("session_errors") if($found);

	my $expires = time + $INACTIVE_TIMEOUT * 60;

	lock_file($sessions_file);
	local *FH;
	exit_message("session_errors") unless(open FH, ">>$sessions_file");
	print FH "$session_id:$user:active:$expires\n";
	close FH;
	unlock_file($sessions_file);

	return ($session_id, $expires);
}

# PBKDF2 for password hashing
# http://www.ict.griffith.edu.au/anthony/software/pbkdf2.pl
# Anthony Thyssen
sub get_pbkdf2_key{
	# key length: 128
	my ($password, $salt) = @_;
	my $prf = \&hmac_sha1;
	my $iter = 8192;
	my $keylen = 64;
	return unpack("H*", pbkdf2($prf, $password, $salt, $iter, $keylen));
}

# http://www.perlmonks.org/?node_id=631963
# Thanks to Jochen Hoenicke <hoenicke@gmail.com>
# (one of the authors of Palm Keyring)
sub pbkdf2{
	my ($prf, $password, $salt, $iter, $keylen) = @_;
	my ($k, $t, $u, $ui, $i);
	$t = "";
	for($k = 1; length($t) < $keylen; $k++){
		$u = $ui = hmac_sha1($salt.pack('N', $k), $password);
		for($i = 1; $i < $iter; $i++){
			$ui = hmac_sha1($ui, $password);
			$u ^= $ui;
		}
		$t .= $u;
	}
	return substr $t, 0, $keylen;
}

sub hash_password{
	# hashed password length: 2*8+128=144
	my ($user, $pw, $salt) = @_;
	$salt = generate_salt() unless(defined $salt);
	return unpack("H*", $salt).get_pbkdf2_key("$user:$salt:$pw", $salt);

}

sub generate_password_set_token{
	# password set token length: 64+1+...
	my $user = shift;
	return generate_random_string(64).".".
		(time + $SET_PASSWORD_TIMEOUT * 60);
}

sub generate_password_reset_token{
	# password reset token length: 64+1+...
	my $user = shift;
	return generate_random_string(64).".".
		(time + $RESET_PASSWORD_TIMEOUT * 60);
}

sub send_email{
	my ($email_address, $subject, $text) = @_;
	eval "use MIME::Lite;";
	exit_message("perl_module_not_installed", "MIME::Lite") if($@);

	if($smtp_server ne ""){
		if($smtp_port ne ""){
			if($smtp_username ne "" && $smtp_password ne ""){
				MIME::Lite->send("smtp", $smtp_server,
					Port=>$smtp_port,
					AuthUser=>$smtp_username,
					AuthPass=>$smtp_password);
			}else{
				MIME::Lite->send("smtp", $smtp_server,
					Port=>$smtp_port);
			}
		}else{
			if($smtp_username ne "" && $smtp_password ne ""){
				MIME::Lite->send("smtp", $smtp_server,
					AuthUser=>$smtp_username,
					AuthPass=>$smtp_password);
			}else{
				MIME::Lite->send("smtp", $smtp_server);
			}
		}
	}
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
<form class="search_input" action="$CGI" method="get">
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
	my ($page, $comment, $direction, $rows, $cols, $mode) = @_;
	$page = $PAGE if($page eq "");
	$comment = "comment" if($comment eq "");
	$direction = "down" if($direction eq "");
	$rows = "6" if($rows eq "");
	$cols = "80" if($cols eq "");
	exit_message("invalid_comment_tag", $comment)
		unless($comment =~ m/^[a-zA-Z0-9_-]+$/);

	my $write = get_msg("comment_form_write");
	my $form = <<EOT;
<form class="comment_input" action="$CGI?comment=$comment" method="post">
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
	my ($header_file, $footer_file);

	unless($wiki){
		($header_file, $footer_file) = ($HEADER_FILE, $FOOTER_FILE);
	}else{
		($header_file, $footer_file) =
			($WIKI_HEADER_FILE, $WIKI_FOOTER_FILE);
	}

	$begin_parsing = \&begin_parsing unless(defined($begin_parsing));
	$parse_line = \&parse_line unless(defined($parse_line));
	$end_parsing = \&end_parsing unless(defined($end_parsing));

	$begin_parsing->();
	foreach my $f ($header_file, $file, $footer_file){
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
	my ($header_file, $footer_file);

	unless($wiki){
		($header_file, $footer_file) = ($HEADER_FILE, $FOOTER_FILE);
	}else{
		($header_file, $footer_file) =
			($WIKI_HEADER_FILE, $WIKI_FOOTER_FILE);
	}

	$begin_parsing = \&begin_parsing unless(defined($begin_parsing));
	$parse_line = \&parse_line unless(defined($parse_line));
	$end_parsing = \&end_parsing unless(defined($end_parsing));

	$begin_parsing->();
	if($header_file ne "" && open UNIQKI_FH, "<", $header_file){
		$parse_line->($_) while(<UNIQKI_FH>);
		close UNIQKI_FH;
	}

	my @lines = split /\n/, $txt, -1; $#lines--;
	$parse_line->($_) foreach(@lines);

	if($footer_file ne "" && open UNIQKI_FH, "<", $footer_file){
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

	my @lines = split /\n/, $txt, -1; $#lines--;
	$parse_line->($_) foreach(@lines);

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
	if(!$pre && m/^(?!#(?:no)?regex)/){
		for(my $i=$re_i_start; $i<$re_i; $i++){
			eval "s\x1e$re[$i]\x1e$re_sub[$i]\x1eg;";
		}
		if(m/\n/){
			local $re_i_start = $re_i;
			my @lines = split /\n/, $_, -1;
			$parse_line->($_) foreach(@lines);
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
		if($li_i > 0 && !(m/^(?:( *)[*+-]|:.*?:) / &&
				length($1)%2 == 0)){
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
	if(m/^#regex (.)(.+)(?<!\\)\1(.*)(?<!\\)\1$/){
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
		# Treat a single backslash as an escape character.
		s/\\(?![\\a-zA-Z0-9])/\x00/g;
		# Don't allow access to variables in a wiki page.
		s/\$/\\\$/g if($wiki);
		$re_sub[$i] = $_;
		return;
	}
	# Clear regular expressions
	if(m/^#noregex(?:| (.)(.+)(?<!\\)\1)$/){
		if($2 eq ""){
			$re_i = 0;
			$#re = $#re_sub = -1;
		}else{
			for(my $i=0; $i<$re_i; $i++){
				if($re[$i] eq $2){
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
		$text .= "$1\n";
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
		$text .= `$1`;
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
	s#\!\!(.*?)\!\!#<mark>$1</mark>#g;
	# Percent-encode links inside tags
	s#(<[^>]*)(.)((?:$protocol).*?)(\2[^>]*>)#$1$2@{[encode_url($3)]}$4#ogi;
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
				for(; $li_i>=0 && ($li[$li_i] ne $tag ||
					$li_attr[$li_i] ne $attr); $li_i--){
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

END{
	while(my $file = each %locked_files){
		unlock_file($file);
	}
}

if($PAGE eq $CGI && $FILE ne ""){
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
}

handle_session();

if(!is_logged_in()){
if($QUERY_STRING eq "login"){
	if($REQUEST_METHOD eq "GET"){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?login		GET login request: Login form
		print_login();
		exit;
	}else{
#-------------------------------------------------------------------------------
# u.cgi/PAGE?login		POST login request: Check credentials
		my %var = get_var();
		authenticate_user($var{user}, $var{pw}, $var{logout_others});
	}
}elsif($QUERY_STRING eq "loginout"){
#-------------------------------------------------------------------------------
# u.cgi?loginout		Loginout
# u.cgi/PAGE?loginout		Loginout
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?login");
}
}elsif($QUERY_STRING eq "loginout"){
#-------------------------------------------------------------------------------
# u.cgi?loginout		Loginout
# u.cgi/PAGE?loginout		Loginout
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?logout");
}

{
#-------------------------------------------------------------------------------
# Is this page wiki?
	my $page;
	local *FH;
	if($PAGE eq "" && ($QUERY_STRING eq "login" || $QUERY_STRING eq "")){
		$page = $INDEX_PAGE;
	}else{
		$page = $PAGE;
	}
	$wiki = 0;
	if($page ne ""){
		if(-f "$page.txt"){
			open FH, "$page.txt";
			$wiki = 1 if(<FH> eq "#!wiki\n");
			close FH;
		}elsif($WIKI_ALLOWED_PAGES ne "" &&
			$page =~ m/$WIKI_ALLOWED_PAGES/o){
			$wiki = 1;
		}
	}
}

if($QUERY_STRING eq "css"){
#-------------------------------------------------------------------------------
# u.cgi?css			Print CSS
	print_css(2);
	exit;
}elsif($QUERY_STRING eq "js"){
#-------------------------------------------------------------------------------
# u.cgi?js			Print JavaScript
	print_js(2);
	exit;
}elsif($QUERY_STRING eq "user_info"){
#-------------------------------------------------------------------------------
# u.cgi?user_info		Print user information
	exit_text("$USER:$admin:".has_read_access().":".has_write_access());
}elsif($QUERY_STRING eq "forgot_password"){
#-------------------------------------------------------------------------------
# u.cgi?forgot_password		Forgot password
# u.cgi/PAGE?forgot_password	Forgot password
	if($REQUEST_METHOD eq "GET"){
		print_forgot_password();
		exit;
	}

	my %var = get_var();
	if($var{user} eq "" && $var{email_address} eq ""){
		exit_message("enter_username_or_email_address");
	}
	my ($user, $pw, $group, $email_address, $reset_token);
	$user = "";
	if($var{email_address} ne ""){
		if(!is_email_address($var{email_address})){
			exit_message("check_email_address");
		}
		($user, $pw, $group, $email_address, $reset_token) =
			find_user_info_by_email_address($var{email_address});
		unless(defined $user){
			exit_message("email_address_not_found",
				$var{email_address});
		}
		if($var{user} ne "" && $var{user} ne $user){
			exit_message("user_info_mismatch");
		}
	}
	if($user eq ""){
		($user, $pw, $group, $email_address, $reset_token) =
			find_user_info($var{user});
		unless(defined $user){
			exit_message("user_not_found", $var{user});
		}
	}

	exit_message("user_blocked", $user) if($pw eq "blocked");
	exit_message("password_reset_token_still_valid")
		if(is_password_reset_token_valid($reset_token));

	$reset_token = generate_password_reset_token($user);

	my $new_pw = "";
	my $reset_token_added = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$user:/){
				$reset_token_added = 1;
				my @items = split /:/;
				$_ = "$user:$items[1]:$items[2]:$items[3]:$reset_token\n";
			}
			$new_pw .= $_;
		}
		close FH;
	}elsif($adminpw =~ m/^$user:/){
		$reset_token_added = 1;
		my @items = split /:/, $adminpw;
		$new_pw = "$user:$items[1]:$items[2]:$items[3]:$reset_token\n";
	}

	# Something's wrong because a username already found does not exist.
	exit_message("internal_errors") unless($reset_token_added);

	my $link = "$HTTP_BASE$SCRIPT_NAME?reset_password=$reset_token";
	my $subject = get_msg("reset_password_email_subject", $DOC_BASE);
	my $text = get_msg("reset_password_email_text", $var{user}, $DOC_BASE,
		$link, $RESET_PASSWORD_TIMEOUT);
	if(!send_email($email_address, $subject, $text)){
		exit_message("email_notification_failed", $user,
			$email_address);
	}

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "reset_password" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi?reset_password		Reset password
# u.cgi/PAGE?reset_password	Reset password
	my %var = get_var();
	exit_message("invalid_password_reset_token")
		unless(is_password_reset_token_valid($var{reset_token}));
	my ($user, $saved_pw, $group, $email_address) =
		find_user_info_by_password_reset_token($var{reset_token});
	exit_message("password_reset_token_not_found") unless(defined $user);

	if($var{pw} ne $var{pw2}){
		exit_message("confirm_password");
	}
	unless(is_password($var{pw})){
		exit_message("check_password");
	}

	my $new_pw = "";
	my $reset = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$user:/){
				$reset = 1;
				my @items = split /:/;
				my $pw = hash_password($user, $var{pw});
				my $userline = "$user:$pw:$items[2]:$items[3]:\n";
				$_ = $userline;
			}
			$new_pw .= $_;
		}
		close FH;
	}
	# Password reset token cannot be found this time?
	exit_message("internal_errors") unless($reset);

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING =~ m/^reset_password=([a-zA-Z0-9]{8}[0-9a-f]{40}\.([0-9]+))$/){
#-------------------------------------------------------------------------------
# u.cgi?reset_password=token	Reset password
# u.cgi/PAGE?reset_password=token Reset password
	my $reset_token = $1;
	my $expires = $2;

	my $time = time;
	if($time >= $expires){
		clear_password_reset_token($reset_token);
		exit_message("password_reset_token_expired");
	}

	local $PASSWORD_RESET_TOKEN = $reset_token;
	print_reset_password();
	exit;
}elsif($QUERY_STRING eq "manage_myself"){
#-------------------------------------------------------------------------------
# u.cgi?manage_myself		Manage myself
# u.cgi/PAGE?manage_myself	Manage myself
	print_manage_myself();
	exit;
}elsif($QUERY_STRING eq "update_myself" && $REQUEST_METHOD eq "POST" && is_logged_in()){
#-------------------------------------------------------------------------------
# u.cgi?update_myself		Update myself
# u.cgi/PAGE?update_myself	Update myself
	my %var = get_var();
	if($var{pw} ne $var{pw2}){
		exit_message("confirm_password");
	}
	if($var{pw} ne "" && !is_password($var{pw})){
		exit_message("check_password");
	}
	if($var{pw} eq "" && $var{email_address} eq ""){
		exit_message("enter_user_info_to_update");
	}

	my $new_pw = "";
	my $updated = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$USER:/){
				$updated = 1;
				my @items = split /:/;
				my $pw = $var{pw} ne "" ?
					hash_password($USER, $var{pw}) :
					$items[1];
				my $group = $items[2];
				my $email_address = $var{email_address} ne "" ?
					$var{email_address} : $items[3];
				my $reset_token = $items[4];
				# new line from $items[4]
				my $userline = "$USER:$pw:$group:$email_address:$reset_token";
				if($userline eq $_){
					close FH;
					exit_message("enter_user_info_to_update", $USER);
				}
				$_ = $userline;
			}
			$new_pw .= $_;
		}
		close FH;
	}else{
		my @items = split /:/, $adminpw;
		if($USER ne $items[0]){
			# Something's wrong because you're the only user, but
			# the user line in this script is not you! How did you
			# login?
			exit_message("internal_errors");
		}

		$updated = 1;
		my $pw = $var{pw} ne "" ? hash_password($USER, $var{pw}) :
			$items[1];
		my $group = $items[2];
		my $email_address = $var{email_address} ne "" ?
			$var{email_address} : $items[3];
		my $reset_token = $items[4];
		# new line from $items[4]
		my $userline = "$USER:$pw:$group:$email_address:$reset_token";
		if($userline eq $adminpw){
			exit_message("enter_user_info_to_update", $USER);
		}
		$new_pw = "$userline\n";
	}
	# How did you login when your username is not found?
	exit_message("internal_errors") unless($updated);

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_myself");
}elsif($QUERY_STRING eq "delete_myself" && $REQUEST_METHOD eq "POST" && is_logged_in()){
#-------------------------------------------------------------------------------
# u.cgi?delete_myself		Delete myself
# u.cgi/PAGE?delete_myself	Delete myself
	my $new_pw = "";
	my $deleted = 0;
	my $nadmins = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			$nadmins++ if($admin && m/^[^:]*:[^:]*:admin:/);
			if(m/^$USER:/){
				$deleted = 1;
				next;
			}
			$new_pw .= $_;
		}
		close FH;
	}
	# How did you login when your username is not found?
	exit_message("internal_errors") unless($deleted);

	# You cannot delete yourself when you are the only admin.
	exit_message("cannot_delete_only_admin") if($nadmins == 1);

	clear_sessions($USER);

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif(!has_read_access()){
#-------------------------------------------------------------------------------
# Read-secured
	exit_message("read_secured");
}elsif($QUERY_STRING eq "login" || $QUERY_STRING eq ""){
#-------------------------------------------------------------------------------
# u.cgi?ACTION			User has to login to perform ACTION
# u.cgi/PAGE?ACTION		User has to login to perform ACTION
# u.cgi?login			After a successful login
# u.cgi/PAGE?login		After a successful login
# u.cgi				No action specified
# u.cgi/PAGE			No action specified
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$INDEX_PAGE") if($PAGE eq "");
	unless(-f "$PAGE.txt"){
		my $path = substr $PATH_INFO, 1;
		exit_redirect("$HTTP_BASE$PATH_INFO") if(-d $path || -f $path);

		my $msg_id = has_write_access() ?
			"create_page" : "page_not_found";
		exit_message($msg_id, $PAGE);
	}
################################################################################
# User actions
}elsif($QUERY_STRING =~ m/^goto(?:[&=].+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?goto			Create the goto form
# u.cgi?goto=PAGE		Go to or create PAGE using a form (admin only)
	my %var = get_var();
	if($var{goto} eq ""){
		local $TITLE = get_msg("goto_form");
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
		exit_message($msg_id, $PAGE);
	}
}elsif($QUERY_STRING =~ m/^diff(?:=(-?[0-9]+))?$/){
#-------------------------------------------------------------------------------
# u.cgi/PAGE?diff		Diff current and previous version
# u.cgi/PAGE?diff=([0-9]+)	Diff current and \1 version
# u.cgi/PAGE?diff=-([0-9]+)	Diff current and current-\1 version
	unless(-f "$PAGE.txt"){
		exit_message("page_not_found", $PAGE);
	}

	my $current_version = get_version($PAGE);
	my $version = $1 > 0 ? $1 : $current_version + ($1 < 0 ? $1 : -1);

	if($version >= $current_version || $version <= 0){
		exit_message("current_version", $PAGE, $current_version)
	}

	my $title = get_msg("differences", $PAGE, $version, $current_version);
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
		last if($version == $1 - 1);
	}
	close FH;

	print_header();
	print qq(<div id="diff">\n<h1>$title</h1>\n);

	my @line0 = split /\n/, $text, -1; $#line0--;
	my @line1 = split /\n/, $current_text, -1; $#line1--;
	my ($s, @delta) = lcs(\@line0, \@line1);
	my $m = $s;
	my $n;
	for($n=0; $n<$s; $n++){
		$_ = $line1[$n];
		s/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g;
		print qq(<div class="diff_unchanged">= $_</div>\n);
	}
	eval "use Encode qw(decode);";
	my $encode = $@ ? 0 : 1;
	for(my $i=0; $i<=$#delta; $i++,$m++,$n++){
		my ($x, $y) = split /,/, $delta[$i];
		if($x > $m && $y > $n){
			for(; $m<$x&&$n<$y; $m++,$n++){
				print qq(<div class="diff_modified">* );
				my $l0 = $line0[$m];
				my $l1 = $line1[$n];
				if($encode){
					$l0 = decode($CHARSET, $l0);
					$l1 = decode($CHARSET, $l1);
				}
				my @l0 = split //, $l0, -1; $#l0--;
				my @l1 = split //, $l1, -1; $#l1--;
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
		$msg_id = $var{ls} eq "rc" ? "recent_changes" :
			($var{ls} eq "oc" ? "old_changes" :
			($var{ls} eq "za" ? "all_pages_reversed" :
			"all_pages"));
		$title = get_msg($msg_id);
	}else{
		$msg_id = $var{ls} eq "rc" ? "recent_changes_matching" :
			($var{ls} eq "oc" ? "old_changes_matching" :
			($var{ls} eq "za" ? "all_pages_reversed_matching" :
			"all_pages_matching"));
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
	(my $site_title = $SITE_TITLE) =~ s/<[^>]*>//g;
	(my $site_description = $SITE_DESCRIPTION) =~ s/<[^>]*>//g;
	print <<EOT;
Content-Type: text/xml

<?xml version="1.0" encoding="$CHARSET"?>
<rss version="2.0">
<channel>
<title>$site_title</title>
<link>$DOC_BASE</link>
<description>$site_description</description>
EOT
	undef $/;
	$i = 0;
	foreach(reverse sort @list){
		my ($time, $page) = m/^[0-9]+ (.+? GMT) (.*)$/;
		local *FH;
		open FH, "$page.html";
		my $text = <FH>;
		close FH;

		$text =~ s/\r//g;
		$text =~ s/^.*<!-- start text -->|<!-- end text -->.*$//sgi;

		my $has_more = ($text =~ s/<!-- more -->.*$//s);
		my $title;
		if($text =~ m#<h1[^>]*>(.+?)</h1>(.*)$#si){
			$title = $1;
			$text = $2;
			$title =~ s/<[^>]*>//g;
			$title =~ s/&[^ ]*;/ /g;
			$title =~ s/[ \t\n]+/ /g;
			$title =~ s/^ //;
			$title =~ s/ $//;
		}else{
			$title = $page;
		}
		$text =~ s#<(script|style).*?</\1>##sgi;
		$text =~ s/<[^>]*>//g;
		$text =~ s/&[^ ]*;/ /g;
		$text =~ s/[ \t\n]+/ /g;
		$text =~ s/^ //;
		$text =~ s/ $//;
		if($text =~ m/^((?:[^ ]+ ){20})/){
			$text = "$1...";
		}elsif($has_more){
			$text .= " ...";
		}
		print <<EOT;
<item>
<title>$title</title>
<link>$DOC_BASE/$page.html</link>
<description>$text</description>
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
		local $TITLE = get_msg("search_form");
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
		$title = get_msg("search", $query);
	}else{
		$title = get_msg("search_matching", $var{glob}, $query);
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

		$text =~ s/^.*<!-- start text -->|<!-- end text -->.*$//sgi;
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
			exit_message("specify_comment_page");
		}elsif(!-f "$PAGE.txt"){
			exit_message("page_not_found", $PAGE);
		}

		local $TITLE = get_msg("comment_form");
		print_header();
		create_comment_form($PAGE, $var{comment}, $var{direction},
			$var{rows}, $var{cols}, 1);
		print_footer();
		exit;
	}
	exit unless(verify_input("comment", \%var));

	$PAGE = $var{page};
	exit_message("page_not_found", $PAGE) unless(-f "$PAGE.txt");

	exit_message("invalid_comment_tag", $var{comment})
		unless($var{comment} =~ m/^[a-zA-Z0-9_-]+$/);

	$var{text} = escape_comment($var{text});

	my $TEXT = "";
	my $time = format_time(time);
	my $added = 0;

	lock_file("$PAGE.txt");
	local *FH;
	if(open FH, "$PAGE.txt"){
		while(<FH>){
			if(m/^#%$var{comment}$/){
				if($var{direction} eq "up"){
					$TEXT .= "$_#%$time\n$var{text}\n\n";
				}else{
					$TEXT .= "#%$time\n$var{text}\n\n$_";
				}
				$added = 1;
			}else{
				$TEXT .= $_;
			}
		}
		close FH;
	}
	exit_message("comment_tag_not_found", "#%$var{comment}") unless($added);
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
		exit_message($msg_id, $PAGE);
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
					exit_message("internal_errors");
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
				exit_message("page_not_found", $PAGE);
			}

			my $version = get_version($PAGE);
			my $backversion = $version - ($1 eq ""?1:$1);

			open FH, "$PAGE.txt"; local $/ = undef;
			$TEXT = <FH>;
			close FH;
			if("#!wiki\n" ne substr $TEXT, 0, 7){
				exit_message("internal_errors");
			}

			if($backversion >= $version || $backversion <= 0){
				close FH;
				exit_message("current_version", $PAGE,
					$version);
			}

			open FH, "$PAGE.txt.v"; local $/ = "\x00\n";
			while(<FH>){
				m/^([0-9]+):.*?\n(.*)\x00\n$/s;
				$TEXT = patch($TEXT, $2);
				last if($backversion == $1 - 1);
			}
			close FH;
			if("#!wiki\n" ne substr $TEXT, 0, 7){
				# Previous version was not a wiki page
				exit_message("not_wiki_page", $PAGE);
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
	}

	my %var = get_var();
	exit unless(verify_input($QUERY_STRING, \%var));

	local *FH;
	my $t = time;
	if($QUERY_STRING eq "wikiupload"){
#-------------------------------------------------------------------------------
# Wiki upload
		exit if($WIKI_ALLOWED_FILES eq "" || !-f "$PAGE.txt" ||
			$var{file} eq "" ||
			$var{file} !~ m/$WIKI_ALLOWED_FILES/oi);

		open FH, "$PAGE.txt";
		if(<FH> ne "#!wiki\n"){
			close FH;
			exit_message("internal_errors");
		}
		close FH;

		mkdir $PAGE, 0755 if(!-d $PAGE);
		open FH, ">$PAGE/$t.$var{file}";
		print FH $var{"file="};
		close FH;
		chmod 0755, "$PAGE/$t.$var{file}" if($hosting eq "awardspace");

		(my $f = $var{file}) =~ s/ /%20/g;
		exit_message("file_uploaded", $var{file}, "$PAGE/$t.$f");
	}
	if(-f "$PAGE.txt"){
		open FH, "$PAGE.txt";
		if(<FH> ne "#!wiki\n"){
			close FH;
			exit_message("internal_errors");
		}
		close FH;
	}

	local $VERSION = $var{version};
	local $TEXT = $var{text};
	if($VERSION != get_version($PAGE) + 1){
		print_updated();
		exit;
	}
	if($var{file} ne "" && $var{file} =~ m/$WIKI_ALLOWED_FILES/oi){
		mkdir $PAGE, 0755 if(!-d $PAGE);
		open FH, ">$PAGE/$t.$var{file}";
		print FH $var{"file="};
		close FH;
		chmod 0755, "$PAGE/$t.$var{file}" if($hosting eq "awardspace");
		if($var{preview} eq ""){
			(my $f = $var{file}) =~ s/ /%20/g;
			$TEXT .= "\n[$PAGE/$t.$f $var{file}]";
		}
	}
	if($var{preview} ne ""){
		my $uploaded;
		if($var{file} ne "" && -f "$PAGE/$t.$var{file}"){
			(my $f = $var{file}) =~ s/ /%20/g;
			$uploaded = get_msg("file_uploaded", $var{file},
				"$PAGE/$t.$f");
		}

		preview($PAGE, $TEXT, $uploaded, 1);
		exit;
	}

	lock_file("$PAGE.txt");
	save($PAGE, "#!wiki\n$TEXT\n");
	unlock_file("$PAGE.txt");
}elsif(!$admin){
################################################################################
# Admin actions
	exit_message("admin_actions_not_allowed");
}elsif($insecure_pw){
#-------------------------------------------------------------------------------
# Admin password is still temporary. No admin actions are allowed other than
# changing the password.
	exit_message("change_admin_password");
}elsif($QUERY_STRING eq "manage_pages"){
#-------------------------------------------------------------------------------
# u.cgi?manage_pages		Manage pages
# u.cgi/PAGE?manage_pages	Manage pages
	print_manage_pages();
	exit;
}elsif($QUERY_STRING eq "backup"){
#-------------------------------------------------------------------------------
# u.cgi?backup			Backup all pages
# u.cgi/PAGE?backup		Backup PAGE
	eval "use Archive::Zip;";
	exit_message("perl_module_not_installed", "Archive::Zip") if($@);

	my $zip = Archive::Zip->new();
	my $file;
	if($PAGE eq ""){
		$file = "uniqki.zip";
		$zip->addTree(".");
	}else{
		$file = "$PAGE.zip";
		foreach("txt", "txt.v", "html"){
			$zip->addFile("$PAGE.$_") if(-f "$PAGE.$_");
		}
		$zip->addTree($PAGE, $PAGE) if(-d $PAGE);
	}
	print <<EOT;
Content-Type: application/zip
Content-Disposition: attachment; filename="$file"

EOT
	$zip->writeToFileHandle(*STDOUT);
	exit;
}elsif($QUERY_STRING eq "restore"){
#-------------------------------------------------------------------------------
# u.cgi?restore			Restore
# u.cgi/PAGE?restore		Restore
	eval "use Archive::Zip;";
	exit_message("perl_module_not_installed", "Archive::Zip") if($@);

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
	(my $cgi = $CGI) =~ s#^(?:/~[^/]+)?/##;
	$zip->removeMember($cgi);
	$zip->removeMember($PASSWORD_FILE);
	foreach($zip->memberNames()){
		$zip->removeMember($_) if(-f $_ && !-w $_);
		if($hosting eq "awardspace" &&
			(m#\.html$# || m#/#)){
			my $member = $zip->memberNamed($_);
			$member->unixFileAttributes(0755);
		}
	}
	$zip->extractTree();
	close $fh;
	unlink $name;

	if($hosting eq "awardspace"){
		foreach($zip->memberNames()){
			chmod 0755, $_ if(m#\.html$# || m#/#);
		}
	}

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_pages");
}elsif($QUERY_STRING =~ m/^refresh(?:&.+)?$/){
#-------------------------------------------------------------------------------
# u.cgi?refresh			Refresh all
# u.cgi?refresh&glob=GLOB	Refresh GLOB pages
	my %var = get_var();
	my $glob = $var{glob};
	my $_begin_parsing = $begin_parsing;
	my $_parse_line = $parse_line;
	my $_end_parsing = $end_parsing;
	my $title = $glob eq "" ? get_msg("refresh_pages") :
		get_msg("refresh_pages_matching", $glob);

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
}elsif($QUERY_STRING eq "manage_users"){
#-------------------------------------------------------------------------------
# u.cgi?manage_users		Manage users
# u.cgi/PAGE?manage_users	Manage users
	print_manage_users();
	exit;
}elsif($QUERY_STRING eq "add_user" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi?add_user		Add user
# u.cgi/PAGE?add_user		Add user
	my %var = get_var();
	if($var{user} eq ""){
		exit_message("enter_username");
	}
	if(!is_username($var{user})){
		exit_message("check_username");
	}
	if($var{user} eq $USER){
		exit_message("cannot_add_yourself");
	}
	if($var{email_address} eq ""){
		exit_message("enter_email_address");
	}
	if(!is_email_address($var{email_address})){
		exit_message("check_email_address");
	}
	if($var{pw} ne $var{pw2}){
		exit_message("confirm_password");
	}
	if($var{pw} ne "" && !is_password($var{pw})){
		exit_message("check_password");
	}

	(my $escaped_email_address = $var{email_address}) =~ s/\./\\./g;
	my $new_pw = "";

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$var{user}:/){
				close FH;
				exit_message("user_already_exists", $var{user});
			}
			if(m/:$escaped_email_address:[^:]*$/i){
				close FH;
				exit_message("email_address_already_registered",
					$var{email_address});
			}
			$new_pw .= $_;
		}
		close FH;
	}elsif($adminpw =~ m/:$escaped_email_address:[^:]*$/i){
		exit_message("email_address_already_registered",
			$var{email_address});
	}else{
		$new_pw = "$adminpw\n";
	}

	# Add a new user if user was not found
	my $group = $var{admin} eq "yes" ? "admin" : "user";
	my $pw;
	my $reset_token;
	if($var{pw} eq ""){
		$pw = "reset";
		$reset_token = generate_password_set_token($var{user});

		my $link = "$HTTP_BASE$SCRIPT_NAME?reset_password=$reset_token";
		my $subject = get_msg("new_user_email_subject", $DOC_BASE);
		my $text = get_msg("new_user_email_text", $var{user}, $DOC_BASE,
			$link, $SET_PASSWORD_TIMEOUT);
		if(!send_email($var{email_address}, $subject, $text)){
			exit_message("email_notification_failed", $var{user},
				$var{email_address});
		}
	}else{
		$pw = hash_password($var{user}, $var{pw});
		$reset_token = "";
	}
	$new_pw .= "$var{user}:$pw:$group:$var{email_address}:$reset_token\n";

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_users");
}elsif($QUERY_STRING eq "update_user" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi?update_user		Update user
# u.cgi/PAGE?update_user	Update user
	my %var = get_var();
	if($var{user} eq ""){
		exit_message("enter_username");
	}
	if(!is_username($var{user})){
		exit_message("check_username");
	}
	if($var{pw} ne $var{pw2}){
		exit_message("confirm_password");
	}
	if($var{pw} ne "" && !is_password($var{pw})){
		exit_message("check_password");
	}
	if($var{pw} eq "" && $var{email_address} eq "" &&
		$var{admin} ne "yes" && $var{admin} ne "no"){
		exit_message("enter_user_info_to_update");
	}

	my $new_pw = "";
	my $updated = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$var{user}:/){
				$updated = 1;
				my @items = split /:/;
				my $pw = $var{pw} ne "" ?
					hash_password($var{user}, $var{pw}) :
					$items[1];
				my $group = $var{admin} eq "yes" ? "admin" :
					($var{admin} eq "no" ? "user" :
						$items[2]);
				my $email_address = $var{email_address} ne "" ?
					$var{email_address} : $items[3];
				my $reset_token = $items[4];
				# new line from $items[4]
				my $userline = "$var{user}:$pw:$group:$email_address:$reset_token";
				if($userline eq $_){
					close FH;
					exit_message("enter_user_info_to_update", $var{user});
				}
				$_ = $userline;
			}
			$new_pw .= $_;
		}
		close FH;
	}else{
		my @items = split /:/, $adminpw;
		if($var{user} ne $items[0]){
			# Something's wrong because you're the only user, but
			# the user line in this script is not you! How did you
			# login?
			exit_message("internal_errors");
		}

		$updated = 1;
		my $pw = $var{pw} ne "" ? hash_password($var{user}, $var{pw}) :
			$items[1];
		my $group = $var{admin} eq "yes" ? "admin" :
			($var{admin} eq "no" ? "user" : $items[2]);
		my $email_address = $var{email_address} ne "" ?
			$var{email_address} : $items[3];
		my $reset_token = $items[4];
		# new line from $items[4]
		my $userline = "$var{user}:$pw:$group:$email_address:$reset_token";
		if($userline eq $adminpw){
			exit_message("enter_user_info_to_update", $var{user});
		}
		$new_pw = "$userline\n";
	}
	exit_message("user_not_found", $var{user}) unless($updated);

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_users");
}elsif($QUERY_STRING eq "block_user" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi?block_user		Block user
# u.cgi/PAGE?block_user		Block user
	my %var = get_var();
	if($var{user} eq ""){
		exit_message("enter_username");
	}
	if(!is_username($var{user})){
		exit_message("check_username");
	}
	if($var{user} eq $USER){
		exit_message("cannot_block_yourself");
	}

	my $new_pw = "";
	my $blocked = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$var{user}:/){
				my @items = split /:/;
				if($items[1] eq "blocked"){
					close FH;
					exit_message("user_already_blocked",
						$var{user});
				}
				$blocked = 1;
				clear_sessions($var{user});
				$_ = "$var{user}:blocked:$items[2]:$items[3]:\n";
			}
			$new_pw .= $_;
		}
		close FH;
	}
	exit_message("user_not_found", $var{user}) unless($blocked);

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_users");
}elsif($QUERY_STRING eq "unblock_user" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi?unblock_user		Unblock user
# u.cgi/PAGE?unblock_user	Unblock user
	my %var = get_var();
	if($var{user} eq ""){
		exit_message("enter_username");
	}
	if(!is_username($var{user})){
		exit_message("check_username");
	}
	if($var{user} eq $USER){
		exit_message("cannot_unblock_yourself");
	}

	if($var{pw} ne $var{pw2}){
		exit_message("confirm_password");
	}
	if($var{pw} ne "" && !is_password($var{pw})){
		exit_message("check_password");
	}

	my $new_pw = "";
	my $unblocked = 0;
	my $reset_token = "";

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$var{user}:/){
				my @items = split /:/;
				if($items[1] ne "blocked"){
					close FH;
					exit_message("user_already_unblocked",
						$var{user});
				}
				$unblocked = 1;
				my $pw;
				if($var{pw} eq ""){
					$pw = "reset";
					$reset_token = generate_password_set_token($var{user});
				}else{
					$pw = hash_password($var{user},
						$var{pw});
					$reset_token = "";
				}
				$_ = "$var{user}:$pw:$items[2]:$items[3]:$reset_token\n";
			}
			$new_pw .= $_;
		}
		close FH;
	}
	exit_message("user_not_found", $var{user}) unless($unblocked);

	if($reset_token ne ""){
		my $link = "$HTTP_BASE$SCRIPT_NAME?reset_password=$reset_token";
		my $subject = get_msg("unblocked_user_email_subject",
			$DOC_BASE);
		my $text = get_msg("unblocked_user_email_text", $var{user},
			$DOC_BASE, $link, $SET_PASSWORD_TIMEOUT);
		if(!send_email($var{email_address}, $subject, $text)){
			exit_message("email_notification_failed", $var{user},
				$var{email_address});
		}
	}

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_users");
}elsif($QUERY_STRING eq "delete_user" && $REQUEST_METHOD eq "POST"){
#-------------------------------------------------------------------------------
# u.cgi?delete_user		Delete user
# u.cgi/PAGE?delete_user	Delete user
	my %var = get_var();
	if($var{user} eq ""){
		exit_message("enter_username");
	}
	if(!is_username($var{user})){
		exit_message("check_username");
	}
	if($var{user} eq $USER){
		exit_message("cannot_delete_yourself");
	}

	my $new_pw = "";
	my $deleted = 0;

	lock_file($PASSWORD_FILE);
	if(-f $PASSWORD_FILE){
		local *FH;
		open FH, $PASSWORD_FILE;
		while(<FH>){
			if(m/^$var{user}:/){
				$deleted = 1;
				clear_sessions($var{user});
				next;
			}
			$new_pw .= $_;
		}
		close FH;
	}
	exit_message("user_not_found", $var{user}) unless($deleted);

	open FH, ">$PASSWORD_FILE";
	print FH $new_pw;
	close FH;
	unlock_file($PASSWORD_FILE);

	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE?manage_users");
}elsif($QUERY_STRING eq "install_password"){
#-------------------------------------------------------------------------------
# u.cgi?install_password	Install the password file, but don't overwrite
# u.cgi/PAGE?install_password	Install the password file, but don't overwrite
	write_pw();
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "install_config"){
#-------------------------------------------------------------------------------
# u.cgi?install_config		Install the config file, but don't overwrite
# u.cgi/PAGE?install_config	Install the config file, but don't overwrite
	process_cfg(1);
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "install_messages"){
#-------------------------------------------------------------------------------
# u.cgi?install_messages	Install the messages file, but don't overwrite
# u.cgi/PAGE?install_messages	Install the messages file, but don't overwrite
	process_msg(1);
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($QUERY_STRING eq "install_template"){
#-------------------------------------------------------------------------------
# u.cgi?install_template	Install the template files, but don't overwrite
# u.cgi/PAGE?install_template	Install the template files, but don't overwrite
	if($TEMPLATE_DIRECTORY ne ""){
		mkdir $TEMPLATE_DIRECTORY, 0755 unless(-d $TEMPLATE_DIRECTORY);
		print_header(1);
		print_footer(1);
		print_login(1);
		print_manage_pages(1);
		print_manage_users(1);
		print_manage_myself(1);
		print_forgot_password(1);
		print_reset_password(1);
		print_message(1);
		print_view(1);
		print_edit(1);
		print_preview(1);
		print_updated(1);
		print_wikiview(1);
		print_wikiedit(1);
		print_wikipreview(1);
		print_css(1);
		print_js(1);
	}
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE");
}elsif($PAGE eq ""){
#-------------------------------------------------------------------------------
# u.cgi?ACTION			Redirect to index
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$INDEX_PAGE");
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
		chmod 0755, "$PAGE/$var{file}" if($hosting eq "awardspace");
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
					last if($version == $1 - 1);
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
		chmod 0755, "$PAGE/$var{file}" if($hosting eq "awardspace");
	}
	if($var{preview} ne ""){
		my $uploaded;
		if($var{file} ne "" && -f "$PAGE/$var{file}"){
			(my $f = $var{file}) =~ s/ /%20/g;
			$uploaded = get_msg("file_uploaded", $var{file},
				"$PAGE/$f");
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
		exit_message("page_not_found", $PAGE);
	}

	lock_file("$PAGE.txt");
	my $current_version = get_version($PAGE);
	my $version = $1 > 0 ? $1 : $current_version + ($1 < 0 ? $1 : -1);
	if($version > 0 && $version < $current_version){
		local *FH;
		open FH, "$PAGE.txt"; local $/ = undef;
		my $text = <FH>;
		close FH;
		open FH, "$PAGE.txt.v"; local $/ = "\x00\n";
		while(<FH>){
			m/^([0-9]+):.*?\n(.*)\x00\n$/s;
			$text = patch($text, $2);
			if($version == $1 - 1){
				$rebuild = 1;
				last;
			}
		}
		if($rebuild){
			local $/ = "\n";
			my $line = <FH>;
			local $/ = undef;
			my $txtv = $line.<FH>;
			close FH;

			open FH, ">$PAGE.txt.v";
			print FH $txtv;
			close FH;

			my @items = split /:/, $line;
			my $time = $items[2];

			open FH, ">$PAGE.txt";
			print FH $text;
			close FH;

			utime $time, $time, "$PAGE.txt";
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
	$PAGE = $INDEX_PAGE;
}

#-------------------------------------------------------------------------------
# Rebuild, if requested, and redirect
make_html($PAGE) if($rebuild);

if($nonwiki_read_access ne "open" || $wiki_read_access ne "open"){
	exit_redirect("$HTTP_BASE$SCRIPT_NAME/$PAGE") if($QUERY_STRING ne "");
	exit_message("page_not_found", $PAGE) unless(-f "$PAGE.html");

	local *FH;
	start_html();
	open FH, "$PAGE.html";
	print <FH>;
	close FH;
	exit;
}

exit_redirect("$DOC_BASE/$PAGE.html");
